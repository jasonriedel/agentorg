import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal
from ..models.gate import Gate
from ..models.event import RunEvent as RunEventModel
from ..models.run import Run, Task, RunStatus, TaskStatus
from ..core.event_bus import EventBus, RunEvent, get_event_bus
from ..core.gate_manager import GateManager, get_gate_manager
from ..core.cost_guard import CostGuard, CostLimitExceeded
from ..core.soul_manager import SoulManager
from ..core.agent_runner import AgentRunner, RunContext, TaskResult
from ..core.workflow_parser import WorkflowDef, TaskDef, resolve_inputs


class Orchestrator:
    def __init__(self, soul_manager: SoulManager, agent_runner: AgentRunner):
        self.soul_manager = soul_manager
        self.agent_runner = agent_runner

    async def execute_run(self, run: Run, workflow_def: WorkflowDef, db: AsyncSession) -> Run:
        bus = get_event_bus()
        guardrails = workflow_def.guardrails
        cost_guard = CostGuard(
            max_cost_usd=guardrails.get("max_cost_usd"),
            max_tokens=guardrails.get("max_tokens"),
        )

        print(f"\n[orchestrator] run={run.id[:8]} workflow='{workflow_def.name}'")

        run.status = RunStatus.running
        run.started_at = datetime.utcnow()
        await db.commit()

        await self._emit(bus, db, RunEvent(run_id=run.id, event_type="run_started", payload={"workflow": workflow_def.name}))

        run_context = RunContext(
            run_id=run.id,
            workflow_name=workflow_def.name,
            phase="",
            shared_context=dict(run.shared_context or {}),
            inputs=run.trigger_payload.get("inputs", {}),
        )
        task_outputs: dict[str, dict] = {}

        try:
            for phase in workflow_def.phases:
                print(f"\n[orchestrator] phase={phase}")
                run.phase = phase
                run_context.phase = phase
                await db.commit()

                await self._emit(bus, db, RunEvent(run_id=run.id, event_type="phase_started", payload={"phase": phase}))

                phase_tasks = [t for t in workflow_def.tasks if t.phase == phase]
                await self._execute_phase(phase_tasks, run, run_context, task_outputs, bus, cost_guard, db)

                # Flush shared context back to DB after each phase
                run.shared_context = dict(run_context.shared_context)
                await db.commit()

            run.status = RunStatus.completed
            run.completed_at = datetime.utcnow()
            await db.commit()

            await self._emit(bus, db, RunEvent(
                run_id=run.id,
                event_type="run_completed",
                payload={"cost_usd": run.cost_usd, "token_count": run.token_count},
            ))
            print(f"\n[orchestrator] completed — ${run.cost_usd:.4f}")

        except CostLimitExceeded as e:
            run.status = RunStatus.failed
            run.error = str(e)
            run.completed_at = datetime.utcnow()
            await db.commit()
            await self._emit(bus, db, RunEvent(run_id=run.id, event_type="run_failed", payload={"error": str(e)}))

        except Exception as e:
            run.status = RunStatus.failed
            run.error = str(e)
            run.completed_at = datetime.utcnow()
            await db.commit()
            await self._emit(bus, db, RunEvent(run_id=run.id, event_type="run_failed", payload={"error": str(e)}))
            print(f"\n[orchestrator] FAILED: {e}")
            raise

        return run

    async def _execute_phase(
        self,
        phase_tasks: list[TaskDef],
        run: Run,
        run_context: RunContext,
        task_outputs: dict[str, dict],
        bus: EventBus,
        cost_guard: CostGuard,
        db: AsyncSession,
    ) -> None:
        pending = {t.id: t for t in phase_tasks}
        asyncio_to_id: dict[asyncio.Task, str] = {}
        in_progress: dict[str, asyncio.Task] = {}

        while pending or in_progress:
            # Launch all tasks whose deps are now satisfied
            for task_id in list(pending):
                task_def = pending[task_id]
                if self._deps_met(task_def, task_outputs):
                    del pending[task_id]
                    cost_guard.check(run.cost_usd, run.token_count, run.id)
                    coro = self._dispatch_task(task_def, run, run_context, task_outputs, bus, db)
                    at = asyncio.create_task(coro, name=f"task:{task_id}")
                    in_progress[task_id] = at
                    asyncio_to_id[at] = task_id

            if not in_progress:
                # Remaining pending tasks have unsatisfiable deps — skip them
                for task_id, task_def in pending.items():
                    print(f"  [orchestrator] skipping {task_id}: deps never satisfied")
                break

            done_set, _ = await asyncio.wait(in_progress.values(), return_when=asyncio.FIRST_COMPLETED)

            for done_at in done_set:
                task_id = asyncio_to_id.pop(done_at)
                del in_progress[task_id]

                result: TaskResult = await done_at  # re-raises on failure

                task_outputs[task_id] = result.outputs
                for k, v in result.outputs.items():
                    run_context.shared_context[k] = v

                # Update run totals in the orchestrator's session
                async with AsyncSessionLocal() as update_db:
                    res = await update_db.execute(select(Run).where(Run.id == run.id))
                    live_run = res.scalar_one()
                    live_run.cost_usd += result.cost_usd
                    live_run.token_count += result.token_count
                    await update_db.commit()

                # Keep in-memory run in sync
                run.cost_usd += result.cost_usd
                run.token_count += result.token_count

                if cost_guard.warn_approaching(run.cost_usd):
                    await self._emit(bus, db, RunEvent(
                        run_id=run.id,
                        event_type="cost_warning",
                        payload={"cost_usd": run.cost_usd, "limit_usd": cost_guard.max_cost_usd},
                    ))

    async def _dispatch_task(
        self,
        task_def: TaskDef,
        run: Run,
        run_context: RunContext,
        task_outputs: dict[str, dict],
        bus: EventBus,
        db: AsyncSession,
    ) -> TaskResult:
        if task_def.task_type == "human_gate":
            return await self._run_gate(task_def, run, run_context, bus, db)
        return await self._run_agent_task(task_def, run, run_context, task_outputs, bus)

    async def _run_agent_task(
        self,
        task_def: TaskDef,
        run: Run,
        run_context: RunContext,
        task_outputs: dict[str, dict],
        bus: EventBus,
    ) -> TaskResult:
        async with AsyncSessionLocal() as db:
            db_task = Task(
                run_id=run.id,
                agent_slug=task_def.agent,
                name=task_def.name,
                phase=task_def.phase,
                depends_on=task_def.depends_on,
                status=TaskStatus.running,
                started_at=datetime.utcnow(),
            )
            db.add(db_task)
            await db.commit()
            await db.refresh(db_task)

            resolved_inputs = resolve_inputs(task_def.inputs, run_context.inputs, task_outputs)
            db_task.input_context = resolved_inputs
            await db.commit()

            await bus.emit(RunEvent(
                run_id=run.id,
                task_id=db_task.id,
                event_type="task_started",
                payload={"task": task_def.name, "agent": task_def.agent},
            ))

            try:
                soul = self.soul_manager.load(task_def.agent)
                result = await self.agent_runner.run_task(
                    task_id=db_task.id,
                    task_name=task_def.name,
                    task_description=task_def.description,
                    agent_soul=soul,
                    run_context=run_context,
                    task_inputs=resolved_inputs,
                    event_bus=bus,
                )

                db_task.status = TaskStatus.completed
                db_task.output_summary = result.summary
                db_task.full_output = result.full_output
                db_task.outputs = result.outputs
                db_task.tool_calls = result.tool_calls_made
                db_task.token_count = result.token_count
                db_task.cost_usd = result.cost_usd
                db_task.completed_at = datetime.utcnow()
                await db.commit()

                await bus.emit(RunEvent(
                    run_id=run.id,
                    task_id=db_task.id,
                    event_type="task_completed",
                    payload={"task": task_def.name, "outputs": list(result.outputs.keys()), "cost_usd": result.cost_usd},
                ))

                return result

            except Exception as e:
                db_task.status = TaskStatus.failed
                db_task.error = str(e)
                db_task.completed_at = datetime.utcnow()
                await db.commit()

                await bus.emit(RunEvent(
                    run_id=run.id,
                    task_id=db_task.id,
                    event_type="task_failed",
                    payload={"task": task_def.name, "error": str(e)},
                ))
                raise

    async def _run_gate(
        self,
        task_def: TaskDef,
        run: Run,
        run_context: RunContext,
        bus: EventBus,
        db: AsyncSession,
    ) -> TaskResult:
        gate_manager = get_gate_manager()

        async with AsyncSessionLocal() as gate_db:
            # Create task record for the gate
            db_task = Task(
                run_id=run.id,
                agent_slug="human",
                name=task_def.name,
                phase=task_def.phase,
                depends_on=task_def.depends_on,
                status=TaskStatus.running,
                started_at=datetime.utcnow(),
            )
            gate_db.add(db_task)
            await gate_db.commit()
            await gate_db.refresh(db_task)

            gate_config = task_def.gate if hasattr(task_def, "gate") and task_def.gate else {}
            message = gate_config.get("message", f"Approve gate: {task_def.name}")

            db_gate = Gate(
                run_id=run.id,
                task_id=db_task.id,
                name=task_def.id,
                message=message,
                status="waiting",
            )
            gate_db.add(db_gate)
            await gate_db.commit()
            await gate_db.refresh(db_gate)

        # Update run status and emit event
        async with AsyncSessionLocal() as status_db:
            live_run = (await status_db.execute(select(Run).where(Run.id == run.id))).scalar_one()
            live_run.status = RunStatus.waiting_human
            await status_db.commit()

        await bus.emit(RunEvent(
            run_id=run.id,
            task_id=db_task.id,
            event_type="human_gate",
            payload={"gate_id": db_gate.id, "gate_name": task_def.name, "message": message},
        ))

        print(f"  [gate] '{task_def.name}' waiting for human approval (gate_id={db_gate.id[:8]})")

        # Block until resolved
        resolution = await gate_manager.wait(db_gate.id)

        # Persist resolution and restore run status
        async with AsyncSessionLocal() as resolve_db:
            g = (await resolve_db.execute(select(Gate).where(Gate.id == db_gate.id))).scalar_one()
            g.status = resolution.action
            g.response = {"action": resolution.action, "feedback": resolution.feedback}
            g.resolved_at = datetime.utcnow()

            t = (await resolve_db.execute(select(Task).where(Task.id == db_task.id))).scalar_one()
            t.status = TaskStatus.completed
            t.completed_at = datetime.utcnow()
            t.outputs = {"gate_result": resolution.action, "feedback": resolution.feedback or ""}

            live_run = (await resolve_db.execute(select(Run).where(Run.id == run.id))).scalar_one()
            live_run.status = RunStatus.running
            await resolve_db.commit()

        await bus.emit(RunEvent(
            run_id=run.id,
            task_id=db_task.id,
            event_type="gate_resolved",
            payload={"gate_id": db_gate.id, "action": resolution.action, "feedback": resolution.feedback},
        ))

        if resolution.action == "rejected":
            raise RuntimeError(f"Gate '{task_def.name}' rejected: {resolution.feedback}")

        return TaskResult(
            task_id=db_task.id,
            summary=f"Gate approved: {task_def.name}",
            full_output="",
            outputs={"gate_result": "approved", "feedback": resolution.feedback or ""},
            tool_calls_made=[],
            token_count=0,
            cost_usd=0.0,
        )

    @staticmethod
    async def _emit(bus: EventBus, db: AsyncSession, event: RunEvent) -> None:
        await bus.emit(event)
        db.add(RunEventModel(
            id=event.id,
            run_id=event.run_id,
            task_id=event.task_id,
            event_type=event.event_type,
            payload=event.payload,
            created_at=event.created_at,
        ))
        await db.commit()

    @staticmethod
    def _deps_met(task_def: TaskDef, task_outputs: dict[str, dict]) -> bool:
        return all(dep in task_outputs for dep in task_def.depends_on)
