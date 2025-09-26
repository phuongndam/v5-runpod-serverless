import runpod
import json
import requests
import base64
import uuid
import time
import os

# ComfyUI host (local hoặc trong docker)
COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")


# --------------------------------------------------
# Validate Job Input
# --------------------------------------------------
def validate_input(job_input):
    if not job_input:
        return None, "Missing input"
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON input"

    workflow = job_input.get("workflow")
    if not workflow:
        return None, "Missing 'workflow' parameter"

    return {"workflow": workflow}, None


# --------------------------------------------------
# Queue workflow to ComfyUI
# --------------------------------------------------
def queue_workflow(workflow, client_id):
    payload = {"prompt": workflow, "client_id": client_id}
    headers = {"Content-Type": "application/json"}
    resp = requests.post(
        f"http://{COMFY_HOST}/prompt",
        data=json.dumps(payload),
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------
# Get history for prompt_id
# --------------------------------------------------
def get_history(prompt_id):
    resp = requests.get(f"http://{COMFY_HOST}/history/{prompt_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------
# Fetch image data
# --------------------------------------------------
def get_image(filename, subfolder, image_type):
    url = f"http://{COMFY_HOST}/view?filename={filename}&subfolder={subfolder}&type={image_type}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


# --------------------------------------------------
# Handler function (called by RunPod)
# --------------------------------------------------
def handler(job):
    job_input = job["input"]

    validated, error = validate_input(job_input)
    if error:
        return {"error": error}

    workflow = validated["workflow"]
    client_id = str(uuid.uuid4())

    try:
        # Send workflow
        queued = queue_workflow(workflow, client_id)
        prompt_id = queued.get("prompt_id")
        if not prompt_id:
            return {"error": "No prompt_id returned from ComfyUI"}

        # Poll history until done
        for _ in range(60):  # wait up to ~60s
            history = get_history(prompt_id)
            if prompt_id in history:
                prompt_history = history[prompt_id]
                if "outputs" in prompt_history:
                    outputs = prompt_history["outputs"]
                    result_images = []

                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                if img.get("type") == "temp":
                                    continue
                                try:
                                    img_bytes = get_image(
                                        img["filename"],
                                        img.get("subfolder", ""),
                                        img["type"],
                                    )
                                    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                                    result_images.append(
                                        {
                                            "filename": img["filename"],
                                            "data": img_b64,
                                            "type": "base64",
                                        }
                                    )
                                except Exception as e:
                                    return {"error": f"Failed to fetch image: {e}"}

                    return {"status": "completed", "images": result_images}
            time.sleep(1)

        return {"error": "Timeout waiting for workflow to complete"}

    except Exception as e:
        return {"error": str(e)}


# --------------------------------------------------
# Local Test (python rp_handler.py)
# --------------------------------------------------
if __name__ == "__main__":
    print("Running rp_handler locally...")

    # Fake job input for testing
    fake_job = {
        "id": "local-test",
        "input": {
            "workflow": {
                # Đây bạn thay bằng workflow JSON thật của ComfyUI
                "1": {
                    "inputs": {"seed": 42, "steps": 10},
                    "class_type": "EmptyLatentImage",
                    "outputs": ["latent"],
                }
            }
        },
    }

    result = handler(fake_job)
    print("Result:", json.dumps(result, indent=2))
else:
    # RunPod entrypoint
    runpod.serverless.start({"handler": handler})