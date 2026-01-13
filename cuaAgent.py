import asyncio
import base64
import openai
import os

from computer import Computer

openai.api_key = os.environ["OPENAI_API_KEY"]


async def execute_action(computer, action):
    action_type = action.type

    if action_type == "click":
        x = action.x
        y = action.y
        button = action.button
        print(f"Executing click at ({x}, {y}) with button '{button}'")
        await computer.interface.move_cursor(x, y)
        if button == "right":
            await computer.interface.right_click()
        else:
            await computer.interface.left_click()

    elif action_type == "type":
        text = action.text
        print(f"Typing text: {text}")
        await computer.interface.type_text(text)

    elif action_type == "scroll":
        x = action.x
        y = action.y
        scroll_x = action.scroll_x
        scroll_y = action.scroll_y
        print(f"Scrolling at ({x}, {y}) with offsets (scroll_x={scroll_x}, scroll_y={scroll_y})")
        await computer.interface.move_cursor(x, y)
        await computer.interface.scroll(scroll_y)  # Using vertical scroll only

    elif action_type == "keypress":
        keys = action.keys
        for key in keys:
            print(f"Pressing key: {key}")
            # Map common key names to Cua equivalents
            if key.lower() == "enter":
                await computer.interface.press_key("return")
            elif key.lower() == "space":
                await computer.interface.press_key("space")
            else:
                await computer.interface.press_key(key)

    elif action_type == "wait":
        wait_time = action.time
        print(f"Waiting for {wait_time} seconds")
        await asyncio.sleep(wait_time)

    elif action_type == "screenshot":
        print("Taking screenshot")
        # This is handled automatically in the main loop, but we can take an extra one if requested
        screenshot = await computer.interface.screenshot()
        return screenshot

    else:
        print(f"Unrecognized action: {action_type}")



async def cua_openai_loop():

    # Initialize the lume computer instance (macOS sandbox)
    async with Computer(
    provider_type="lume",
    name="cuatest",
) as computer:
     await computer.run()

        # Capture the initial screenshot
    screenshot = await computer.interface.screenshot()
    screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')

        # Initial request to start the loop
        response = openai.responses.create(
            model="computer-use-preview",
            tools=[{
                "type": "computer_use_preview",
                "display_width": 1024,
                "display_height": 768,
                "environment": "mac"
            }],
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Open Safari, download and install Cursor."},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{screenshot_base64}"}
                    ]
                }
            ],
            truncation="auto"
        )

        # Continue the loop until no more computer_call actions
        while True:
            # Check for computer_call actions
            computer_calls = [item for item in response.output if item and item.type == "computer_call"]
            if not computer_calls:
                print("No more computer calls. Loop complete.")
                break

            # Get the first computer call
            call = computer_calls[0]
            last_call_id = call.call_id
            action = call.action
            print("Received action from OpenAI Responses API:", action)

            # Handle any pending safety checks
            if call.pending_safety_checks:
                print("Safety checks pending:", call.pending_safety_checks)
                # In a real implementation, you would want to get user confirmation here
                acknowledged_checks = call.pending_safety_checks
            else:
                acknowledged_checks = []

            # Execute the action
            await execute_action(computer, action)
            await asyncio.sleep(1)  # Allow time for changes to take effect

            # Capture new screenshot after action
            new_screenshot = await computer.interface.screenshot()
            new_screenshot_base64 = base64.b64encode(new_screenshot).decode('utf-8')

            # Send the screenshot back as computer_call_output
            response = openai.responses.create(
                model="computer-use-preview",
                tools=[{
                    "type": "computer_use_preview",
                    "display_width": 1024,
                    "display_height": 768,
                    "environment": "mac"
                }],
                input=[{
                    "type": "computer_call_output",
                    "call_id": last_call_id,
                    "acknowledged_safety_checks": acknowledged_checks,
                    "output": {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{new_screenshot_base64}"
                    }
                }],
                truncation="auto"
            )

        # End the session
        await computer.stop()

# Run the loop
if __name__ == "__main__":
    asyncio.run(cua_openai_loop())