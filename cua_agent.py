import asyncio
from computer import Computer, Display

async def main():
    async with Computer(
        display=Display(width=1280, height=800),
        memory="8g",
        cpu="4",
        os="macos",
        name="cuatest",
        image="macos-sequoia-cua-sparse:latest",
    ) as computer:
        await computer.run()  # Launch & connect to the sandbox

        print("Connected! Testing screenshot...")

        # Take screenshot - returns bytes
        screenshot_bytes = await computer.interface.screenshot()
        print(f"Screenshot succeeded! Got {len(screenshot_bytes)} bytes")

        # Save screenshot to file
        with open("screenshot.png", "wb") as f:
            f.write(screenshot_bytes)
        print("Screenshot saved to screenshot.png")

        # Try click and type
        print("Testing click...")
        await computer.interface.left_click(100, 100)
        print("Click succeeded!")

        print("Testing type...")
        await computer.interface.type("Hello!")
        print("Type succeeded!")


asyncio.run(main())
