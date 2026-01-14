import asyncio
import base64
import os
from computer import Computer, Display
import anthropic

# Initialize the Anthropic client
client = anthropic.Anthropic()

# Display dimensions (must match what you set in Computer)
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 800


async def execute_tool_action(computer, tool_name, tool_input):
    """Execute a tool action from Claude's response."""

    if tool_name == "computer":
        action = tool_input.get("action")

        if action == "screenshot":
            print("Taking screenshot...")
            screenshot = await computer.interface.screenshot()
            return screenshot

        elif action == "mouse_move":
            x = tool_input.get("coordinate", [0, 0])[0]
            y = tool_input.get("coordinate", [0, 0])[1]
            print(f"Moving mouse to ({x}, {y})")
            await computer.interface.move_cursor(x, y)

        elif action == "left_click":
            x = tool_input.get("coordinate", [None, None])[0]
            y = tool_input.get("coordinate", [None, None])[1]
            if x is not None and y is not None:
                print(f"Left clicking at ({x}, {y})")
                await computer.interface.move_cursor(x, y)
            else:
                print("Left clicking at current position")
            await computer.interface.left_click()

        elif action == "right_click":
            x = tool_input.get("coordinate", [None, None])[0]
            y = tool_input.get("coordinate", [None, None])[1]
            if x is not None and y is not None:
                print(f"Right clicking at ({x}, {y})")
                await computer.interface.move_cursor(x, y)
            else:
                print("Right clicking at current position")
            await computer.interface.right_click()

        elif action == "double_click":
            x = tool_input.get("coordinate", [None, None])[0]
            y = tool_input.get("coordinate", [None, None])[1]
            if x is not None and y is not None:
                print(f"Double clicking at ({x}, {y})")
                await computer.interface.move_cursor(x, y)
            else:
                print("Double clicking at current position")
            await computer.interface.double_click()

        elif action == "type":
            text = tool_input.get("text", "")
            print(f"Typing: {text}")
            await computer.interface.type(text)

        elif action == "key":
            key = tool_input.get("key", "")
            print(f"Pressing key: {key}")
            # Map common key names
            key_map = {
                "Return": "return",
                "Enter": "return",
                "Tab": "tab",
                "Escape": "escape",
                "BackSpace": "backspace",
                "Delete": "delete",
                "space": "space",
                "Up": "up",
                "Down": "down",
                "Left": "left",
                "Right": "right",
            }
            mapped_key = key_map.get(key, key.lower())
            await computer.interface.press_key(mapped_key)

        elif action == "scroll":
            x = tool_input.get("coordinate", [DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2])[0]
            y = tool_input.get("coordinate", [DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2])[1]
            direction = tool_input.get("direction", "down")
            amount = tool_input.get("amount", 3)
            print(f"Scrolling {direction} by {amount} at ({x}, {y})")
            await computer.interface.move_cursor(x, y)
            if direction == "down":
                await computer.interface.scroll_down(amount)
            else:
                await computer.interface.scroll_up(amount)

        elif action == "wait":
            print("Waiting...")
            await asyncio.sleep(1)

        else:
            print(f"Unknown computer action: {action}")

    else:
        print(f"Unknown tool: {tool_name}")

    return None


async def main():
    # Set up the VM
    async with Computer(
        display=Display(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT),
        memory="8g",
        cpu="4",
        os="macos",
        name="cuatest",
        image="macos-sequoia-cua-sparse:latest",
    ) as computer:
        await computer.run()
        print("VM is ready!")

        # Take initial screenshot
        screenshot = await computer.interface.screenshot()
        screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")

        # Initial message with the task
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Open Safari and navigate to google.com. Then search for 'hello world'."
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_base64,
                        },
                    },
                ],
            }
        ]

        # Define the computer use tool
        tools = [
            {
                "type": "computer_20250124",
                "name": "computer",
                "display_width_px": DISPLAY_WIDTH,
                "display_height_px": DISPLAY_HEIGHT,
                "display_number": 1,
            }
        ]

        # Main loop
        while True:
            print("\n--- Calling Claude ---")

            # Call Claude with computer use capability
            response = client.beta.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                tools=tools,
                messages=messages,
                betas=["computer-use-2025-01-24"],
            )

            print(f"Stop reason: {response.stop_reason}")

            # Check if we're done
            if response.stop_reason == "end_turn":
                # Extract any text response
                for block in response.content:
                    if hasattr(block, "text"):
                        print(f"Claude says: {block.text}")
                print("\nTask complete!")
                break

            # Process tool uses
            if response.stop_reason == "tool_use":
                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Process each tool use
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        print(f"\nTool: {tool_name}")
                        print(f"Input: {tool_input}")

                        # Execute the action
                        result = await execute_tool_action(computer, tool_name, tool_input)

                        # Wait a moment for the action to take effect
                        await asyncio.sleep(0.5)

                        # Take a screenshot after the action
                        screenshot = await computer.interface.screenshot()
                        screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")

                        # Add tool result with screenshot
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": screenshot_base64,
                                    },
                                }
                            ],
                        })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })
            else:
                # Unknown stop reason
                print(f"Unknown stop reason: {response.stop_reason}")
                break

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
