import json
import os
import time
from datetime import datetime, timedelta, timezone

import boto3

EC2_CLIENT = boto3.client("ec2", region_name=os.environ.get("AWS_REGION"))
SCHEDULER_CLIENT = boto3.client("scheduler", region_name=os.environ.get("AWS_REGION"))

INSTANCE_ID = os.environ["EC2_INSTANCE_ID"]
AUTO_STOP_SECONDS = int(os.environ.get("AUTO_STOP_SECONDS", "10800"))
STATE_TIMEOUT = int(os.environ.get("STATE_TIMEOUT", "300"))
POLL_INTERVAL = 5
STOP_SCHEDULE_NAME = os.environ.get("STOP_SCHEDULE_NAME", "kgraph-astrolabe-auto-stop")
SCHEDULER_ROLE = os.environ["WAKE_SCHEDULER_ROLE"]
WAKE_LAMBDA_ARN = os.environ["WAKE_LAMBDA_ARN"]


def _instance():
    resp = EC2_CLIENT.describe_instances(InstanceIds=[INSTANCE_ID])
    return resp["Reservations"][0]["Instances"][0]


def _state():
    return _instance()["State"]["Name"]


def _delete_stop_schedule():
    try:
        SCHEDULER_CLIENT.delete_schedule(Name=STOP_SCHEDULE_NAME)
    except SCHEDULER_CLIENT.exceptions.ResourceNotFoundException:
        pass


def _arm_auto_stop():
    """Anti-olvido: schedule one-shot que para la VM en AUTO_STOP_SECONDS.

    Si se encadena un nuevo arranque antes, se regenera el horario.
    """
    _delete_stop_schedule()
    at = datetime.now(timezone.utc) + timedelta(seconds=AUTO_STOP_SECONDS)
    SCHEDULER_CLIENT.create_schedule(
        Name=STOP_SCHEDULE_NAME,
        ScheduleExpression=f"at({at.strftime('%Y-%m-%dT%H:%M:%S')})",
        FlexibleTimeWindow={"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 5},
        ActionAfterCompletion="DELETE",
        State="ENABLED",
        Target={
            "Arn": WAKE_LAMBDA_ARN,
            "RoleArn": SCHEDULER_ROLE,
            "Input": json.dumps({"action": "stop", "via": "auto-stop"}),
        },
    )


def _respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    params = {}
    if isinstance(event, dict):
        if event.get("queryStringParameters"):
            params = event["queryStringParameters"]
        elif isinstance(event.get("action"), str):
            params = event  # invocada por el Scheduler (Input={"action":"stop"})

    action = params.get("action", "start")

    if action == "stop":
        try:
            EC2_CLIENT.stop_instances(InstanceIds=[INSTANCE_ID])
        except Exception:
            pass
        _delete_stop_schedule()
        return _respond(200, {"status": "stopping", "instance": INSTANCE_ID})

    if _state() not in ("running", "pending"):
        EC2_CLIENT.start_instances(InstanceIds=[INSTANCE_ID])

    deadline = time.time() + STATE_TIMEOUT
    state = None
    while time.time() < deadline:
        state = _state()
        if state == "running":
            break
        time.sleep(POLL_INTERVAL)

    if state == "running":
        _arm_auto_stop()
        return _respond(
            200,
            {
                "status": "running",
                "instance": INSTANCE_ID,
                "public_ip": _instance().get("PublicIpAddress"),
            },
        )

    return _respond(
        202,
        {
            "status": state or "unknown",
            "instance": INSTANCE_ID,
            "message": f"Aún no running tras {STATE_TIMEOUT}s; reintenta en unos minutos",
        },
    )