import json
import random
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    scenarios = [
        "processing_order",
        "user_login",
        "fetch_inventory",
        "payment_gateway",
    ]

    scenario = random.choice(scenarios)
    user_id = random.randint(1000, 9999)

    logger.info(f"START scenario={scenario} user_id={user_id}")

    roll = random.random()

    if roll < 0.3:
        logger.error(
            f"ERROR scenario={scenario} user_id={user_id} "
            f"reason=TimeoutException latency_ms=5032 threshold_ms=5000"
        )
        return {"statusCode": 500, "body": json.dumps("timeout")}

    elif roll < 0.5:
        logger.error(
            f"ERROR scenario={scenario} user_id={user_id} "
            f"reason=NullPointerException field=customer_email"
        )
        return {"statusCode": 500, "body": json.dumps("null pointer")}

    elif roll < 0.6:
        logger.warning(
            f"WARN scenario={scenario} user_id={user_id} "
            f"reason=RetryAttempt attempt=3 max_retries=3"
        )

    duration_ms = random.randint(50, 800)
    logger.info(
        f"END scenario={scenario} user_id={user_id} "
        f"status=success duration_ms={duration_ms}"
    )
    return {"statusCode": 200, "body": json.dumps("ok")}
