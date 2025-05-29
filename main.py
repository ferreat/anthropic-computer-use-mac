import asyncio
import os
import sys
import json
import base64

from computer_use_demo.loop import (
    APIProvider,
    sampling_loop, 
)
from computer_use_demo.tools import ToolResult, ToolVersion
from anthropic.types.beta import BetaMessage, BetaMessageParam
from anthropic import APIResponse


class ModelConfig:
    tool_version: ToolVersion
    max_output_tokens: int
    default_output_tokens: int
    has_thinking: bool = False


SONNET_3_5_NEW = ModelConfig(
    tool_version="computer_use_20241022",
    max_output_tokens=1024 * 8,
    default_output_tokens=1024 * 4,
)

SONNET_3_7 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

CLAUDE_4 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

MODEL_TO_MODEL_CONF: dict[str, ModelConfig] = {
    "claude-3-7-sonnet-20250219": SONNET_3_7,
    "claude-opus-4@20250508": CLAUDE_4,
    "claude-sonnet-4-20250514": CLAUDE_4,
    "claude-opus-4-20250514": CLAUDE_4,
}


async def main():
    # Set up your Anthropic API key and model
    api_key = os.getenv("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
    if api_key == "YOUR_API_KEY_HERE":
        raise ValueError(
            "Please first set your API key in the ANTHROPIC_API_KEY environment variable"
        )
    # provider = APIProvider.ANTHROPIC
    # model = "claude-3-5-sonnet-20241022",
    provider = APIProvider.BEDROCK
    # model = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    model = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    model_conf = MODEL_TO_MODEL_CONF['claude-3-7-sonnet-20250219']


    # Check if the instruction is provided via command line arguments
    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
    else:
        instruction = "Save an image of a cat to the desktop."

    print(
        f"Starting Claude 'Computer Use'.\nPress ctrl+c to stop.\nInstructions provided: '{instruction}'"
    )

    # Set up the initial messages
    messages: list[BetaMessageParam] = [
        {
            "role": "user",
            "content": instruction,
        }
    ]

    # Define callbacks (you can customize these)
    def output_callback(content_block):
        if isinstance(content_block, dict) and content_block.get("type") == "text":
            print("Assistant:", content_block.get("text"))

    def tool_output_callback(result: ToolResult, tool_use_id: str):
        if result.output:
            print(f"> Tool Output [{tool_use_id}]:", result.output)
        if result.error:
            print(f"!!! Tool Error [{tool_use_id}]:", result.error)
        if result.base64_image:
            # Save the image to a file if needed
            os.makedirs("screenshots", exist_ok=True)
            image_data = result.base64_image
            with open(f"screenshots/screenshot_{tool_use_id}.png", "wb") as f:
                f.write(base64.b64decode(image_data))
            print(f"Took screenshot screenshot_{tool_use_id}.png")

    def api_response_callback(response: APIResponse[BetaMessage]):
        print(
            "\n---------------\nAPI Response:\n",
            json.dumps(json.loads(response.text)["content"], indent=4),  # type: ignore
            "\n",
        )

    # Run the sampling loop
    messages = await sampling_loop(
        system_prompt_suffix="",
        model=model,
        provider=provider,
        messages=messages,
        output_callback=output_callback,
        tool_output_callback=tool_output_callback,
        api_response_callback=api_response_callback,
        api_key=api_key,
        only_n_most_recent_images=10,
        tool_version=model_conf.tool_version,
        max_tokens=model_conf.default_output_tokens,
        thinking_budget=int(model_conf.default_output_tokens / 2),
        token_efficient_tools_beta=False,
    )
    




if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Encountered Error:\n{e}")
