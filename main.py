import json
import assistant_model


if __name__ == "__main__":

    filepath = "./investor_profiles.json"

    with open(filepath, 'r') as file:
        investor_data = json.load(file)

    investors_list = investor_data["users"]
    # Dummy Testing
    investor_name = investors_list[0]["name"]  # First name
    investor_username = investors_list[0]["username"]  # First username
    investor_password = investors_list[0]["password"]
    investor_tolerance = investors_list[0]["tolerance"]

    manager_obj = assistant_model.AssistantManager(
        name=investor_name, username=investor_username, password=investor_password, tolerance=investor_tolerance)
    file_embed = manager_obj.file_embed
    file_companies = manager_obj.file_companies
    vector_store = manager_obj.vector_store

    bot_name = "Financial Assistant"

    # Instructions during assistant model creation
    instructions_model = f"""You are an Expert Professional Financial Analyst working for a Mutual Funds Company called "Arthur.Inc."
    Your clientele are the investors in the Mutual Funds "Arthur.Inc" company and this company invested its clients' money in various tech companies.
    Currently, "Arthur.Inc" is investing clients' money only in companies that are found in "companies.json" file which you have access to.
    You have access to the companies your clients have invested in and their data.
    All the clients' data is stored in file "investor_profiles.json" that you have access to. 
    Check this "investor_profiles.json" file for the names of the companies a particular client has invested in. 
    You have the power to predict the stocks of companies for the next month based on the current stocks returned by the API function that you have access to. 
    You also have the ability to create beautiful charts, graphs, diagrams, etc displaying the current stock prices and market trends for your clients.
    Also, whenever the stocks API function(s) is called and returns some JSON data, you have to parse and analyze that data and display it to your client and also produce graphs, charts whenever needed.
    Display stocks to your clients even if the stocks function API gives delayed information.
    Use code_interpreter tool that you have for calculations.
    Please address the user as {manager_obj.name}. 
    Always parse and analyze the data returned by the get_current_stocks() API function that you possess to display it to the client whenever needed.
    Do not rush to answers. Take your time before answering. Do not assume that your clients are always correct. Correct them when necessary.
    Try to reassure your clients that their money is in safe hands and they may see profits eventually."""

    # {"type": "retrieval"} is deprecated in v1. Now it's v2.
    tools = [{"type": "code_interpreter"}, {"type": "file_search"}, # {"type": "retrieval"},
             {
        "type": "function",
        "function": {
            "name": "get_current_stocks",
            "description": "Get the current stocks for a specific company",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "The NASDAQ exchange ticker symbol of the company for getting stocks, e.g., AAPL, AMZN, GOOG, TSLA"
                    },
                },
                "required": ["company"]
            }
        }
    }]
    tool_resources = {
        "code_interpreter": {"file_ids": [file_embed.id, file_companies.id]},
        "file_search": {"vector_store_ids": [vector_store.id]},
        # "retrieval": {"file_ids": [file_embed.id, file_companies.id]}
    }
    model = assistant_model.model

    # Instructions during Run
    # instructions_run = f"""Please address the user as {manager_obj.name}.
    #     Always parse and analyze the data returned by the get_stocks() API function that you possess to display it to the client whenever needed.
    # Do not rush to answers. Take your time before answering. Do not assume that your clients are always correct. Correct them when necessary.
    # Try to reassure your clients that their money is in safe hands and they may see profits eventually."""

    # Model Initiation Sequence
    manager_obj.create_assistant(name=bot_name, instructions=instructions_model, tools=tools, tool_resources=tool_resources)  # 1
    manager_obj.create_thread()  # 2
    manager_obj.add_msg_to_thread(role="user", content="Can you show me stocks of companies I invested in?")  # 3
    manager_obj.initiate_run()  # 4
    manager_obj.wait_for_completed()  # 5


