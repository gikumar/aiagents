#app/utility/thread_cleanup_scheduler.py
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from azure.ai.agents.models import ListSortOrder

from .agent_registry import REGISTERED_AGENT_INSTANCES, register_agent_instance, get_agent_instance

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

AGENT_CLASSES = [
    {"name": "OrchestratorAgent", "class_name": "AgentFactory"},
    {"name": "SQLQueryGeneratorAgent", "class_name": "AGSQLQueryGenerator"},
]

KEEP_LAST_N_THREADS = 5
CLEANUP_INTERVAL_MINUTES = 30

# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ThreadCleanupScheduler")

# -----------------------------------------------------------------------------
# Helper to dynamically import agent classes by name
# -----------------------------------------------------------------------------

def get_agent_class_by_name(class_name: str):
    if class_name == "AgentFactory":
        from ..agentfactory import AgentFactory
        return AgentFactory
    elif class_name == "AGSQLQueryGenerator":
        from ..agsqlquerygenerator import AGSQLQueryGenerator
        return AGSQLQueryGenerator
    else:
        raise ValueError(f"Unknown agent class name: {class_name}")

# -----------------------------------------------------------------------------
# Cleanup Logic
# -----------------------------------------------------------------------------

def delete_threads_for_agent(agent_instance, agent_name: str, keep_last_n: int = KEEP_LAST_N_THREADS):
    try:
        agent_client = agent_instance.agent_client
        all_threads = list(agent_client.threads.list(order=ListSortOrder.DESCENDING))

        logger.info(f"[{agent_name}] Total threads: {len(all_threads)}")

        active_ids = []
        if hasattr(agent_instance, "get_active_thread_ids"):
            try:
                active_ids = agent_instance.get_active_thread_ids()
                logger.info(f"[{agent_name}] Active thread IDs (will skip): {active_ids}")
            except Exception as e:
                logger.warning(f"[{agent_name}] Failed to get active thread IDs: {e}")

        threads_to_delete = [
            t for t in all_threads[keep_last_n:]
            if t.id not in active_ids
        ]

        deleted_count = 0
        for thread in threads_to_delete:
            try:
                agent_client.threads.delete(thread.id)
                logger.info(f"[{agent_name}] Deleted thread: {thread.id}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"[{agent_name}] Failed to delete thread {thread.id}: {e}")

        logger.info(f"[{agent_name}] Deleted {deleted_count} threads. Kept {keep_last_n} + active ones.")
    except Exception as e:
        logger.error(f"[{agent_name}] Cleanup failed: {e}", exc_info=True)

def run_thread_cleanup_all_agents():
    logger.info("🧹 Starting thread cleanup cycle...")
    for agent_cfg in AGENT_CLASSES:
        agent_name = agent_cfg["name"]
        class_name = agent_cfg["class_name"]

        if agent_cfg.get("skip_cleanup", False):
            logger.info(f"[{agent_name}] Skipping cleanup as per config.")
            continue

        try:
            agent_class = get_agent_class_by_name(class_name)

            agent_instance = get_agent_instance(agent_name)
            if agent_instance is None:
                agent_instance = agent_class()
                register_agent_instance(agent_name, agent_instance)

            delete_threads_for_agent(agent_instance, agent_name)

            if hasattr(agent_instance, "cleanup_stale_runs"):
                try:
                    agent_instance.cleanup_stale_runs()
                    logger.info(f"[{agent_name}] Stale run cleanup completed.")
                except Exception as e:
                    logger.warning(f"[{agent_name}] cleanup_stale_runs failed: {e}")

        except Exception as e:
            logger.error(f"[{agent_name}] Agent init or cleanup error: {e}", exc_info=True)
    logger.info("Thread cleanup cycle complete.\n")

# -----------------------------------------------------------------------------
# Scheduler Startup (if run standalone)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_thread_cleanup_all_agents, 'interval', minutes=CLEANUP_INTERVAL_MINUTES)
    scheduler.start()
    logger.info(f"Thread cleanup scheduler started (every {CLEANUP_INTERVAL_MINUTES} min)")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Thread cleanup scheduler shut down.")


scheduler_instance = None

def start_thread_cleanup_scheduler():
    global scheduler_instance
    if scheduler_instance is None:
        scheduler_instance = BackgroundScheduler()
        scheduler_instance.add_job(run_thread_cleanup_all_agents, 'interval', minutes=CLEANUP_INTERVAL_MINUTES)
        scheduler_instance.start()
        logger.info(f"Thread cleanup scheduler started (every {CLEANUP_INTERVAL_MINUTES} min)")
