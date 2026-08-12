from core.agent_loop import AgentLoop


def main():
    agent = AgentLoop()

    print("\nZOEY AGENT TEST")
    print("----------------")

    while True:
        message = input("\nYou: ")

        if message.lower().strip() == "exit":
            break

        result = agent.run(message)

        if result.get("type") == "response":
            print(f"Zoey: {result.get('content', '')}")
        else:
            print(f"Zoey: {result}")


if __name__ == "__main__":
    main()