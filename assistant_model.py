import json
import logging
import os
import time
import openai
import requests
from dotenv import load_dotenv, find_dotenv


load_dotenv()
model = "gpt-4-turbo"
filepath_1 = "./investor_profiles.json"
filepath_2 = "./companies.json"


class AssistantManager:
    # Need to hardcode the ids after first run.
    assistant_id = "asst_ZpUUa33VpkZL8xTKoBL94eTY"
    thread_id = "thread_UyL8mxPC2dBk7on41O7H8aYq"

    # Only setup everything but don't create assistant yet.
    def __init__(self, username, password, name, tolerance, model: str = model):
        self.client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.vector_store = None
        self.file_embed = None
        self.file_companies = None
        # User Variables
        self.username = username
        self.password = password
        self.name = name
        self.tolerance = tolerance

        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(assistant_id=AssistantManager.assistant_id)
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(thread_id=AssistantManager.thread_id)

        if not (self.assistant and self.thread):
            # Create a vector store called "Financial Docs"
            vector_store = self.client.beta.vector_stores.create(name="Clients Financial Data")
            # Ready the files for upload to OpenAI
            file_paths = [filepath_1, filepath_2]
            file_streams = [open(path, "rb") for path in file_paths]
            file_batch = self.client.beta.vector_stores.file_batches.upload_and_poll(vector_store_id=vector_store.id, files=file_streams)
            # You can print the status and the file counts of the batch to see the result of this operation.
            print("[INFO] File Batch Status::::", file_batch.status)

            self.vector_store = vector_store

            # Attaching files to the assistant
            with open(filepath_1, "rb") as file:
                response = self.client.files.create(file=file.read(), purpose="assistants")
            self.file_embed = response
            with open(filepath_2, "rb") as file:
                response = self.client.files.create(file=file.read(), purpose="assistants")
            self.file_companies = response

    # Create actual assistant here. # 1
    def create_assistant(self, name, instructions, tools, tool_resources):
        if not self.assistant:
            assistant = self.client.beta.assistants.create(
                name=name, instructions=instructions, tools=tools, tool_resources=tool_resources, model=self.model)
            AssistantManager.assistant_id = assistant.id
            self.assistant = assistant
            print(f"Assistant ID:::: {assistant.id}")

    # 2
    def create_thread(self):
        if not self.thread:
            thread = self.client.beta.threads.create()
            AssistantManager.thread_id = thread.id
            self.thread = thread
            print(f"Thread ID:::: {thread.id}")

    # Runs the assistant. # 4
    def initiate_run(self, instructions=None):
        if self.assistant and self.thread:
            self.run = self.client.beta.threads.runs.create_and_poll(
                assistant_id=self.assistant.id, thread_id=self.thread.id)

    # Adds msgs to the thread. role --> user, assistant # 3
    def add_msg_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(thread_id=self.thread.id, role=role, content=content)

    # Process msgs returned by the model. Only execute this after run() status is completed.
    def process_msgs(self):
        if self.thread:
            messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)
            last_message = messages.data[0]  # Raw
            role = last_message.role
            if last_message.content[0].type == "text":
                response = last_message.content[0].text.value
                print(f"{role.capitalize()}:::: {response}")
            elif last_message.content[0].type == "image_file":
                response = last_message.content[0].image_file.file_id
            # if response is None, then role: NoneType
            return {role: response}

    # Just run this func to embed/attach the file to the assistant.
    # [INFO] file=file.read() should exist because 'as file' makes it an object but not byte stream that the func requires.
    # This func should run before create assistant func.
    # def assistant_file_retrieval(self):
    #     with open(filepath, "rb") as file:
    #         response = self.client.files.create(file=file.read(), purpose="assistants")
    #     self.file_embed = response

    def call_required_functions(self, required_actions):
        if self.run:
            tool_outputs = []
            for action in required_actions['tool_calls']:
                func_name = action['function']['name']
                arguments = json.loads(action['function']['arguments'])

                if func_name == 'get_current_stocks':
                    output = self.get_current_stocks(company=arguments['company'])
                    # print("OUTPUT:::: ", output)
                    tool_outputs.append({"tool_call_id": action['id'], "output": str(output)})
                else:
                    # If func_name other than get_stocks()
                    raise ValueError(f"Unknown Function {func_name}")

            print("Submitting required back to the Assistant....")
            if tool_outputs:
                try:
                    self.client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=self.thread.id, run_id=self.run.id, tool_outputs=tool_outputs)
                    # self.add_msg_to_thread(role="assistant", content="Please analyze the JSON data returned by the get_current_stocks() API function and produce graphs, charts if needed")
                    # print("Tool outputs submitted successfully.")
                    logging.info("Tool outputs submitted successfully.")
                except Exception as e:
                    # print("Failed to submit tool outputs:", e)
                    logging.warning(f"Failed to submit tool outputs: {e}")
            else:
                print("[WARN] No tool outputs to submit.")
                logging.warning("No tool outputs to submit.")

        else:
            # If there is no run obj, then return None
            return

    # 5
    def wait_for_completed(self, sleep: int = 2.5):
        if self.thread and self.run:
            while True:
                # time.sleep(sleep) # No need as I am using create_and_poll() methods.
                # run_status = self.run.get_status()
                run_status = self.client.beta.threads.runs.retrieve(thread_id=self.thread.id, run_id=self.run.id)
                print(f"All Run Statuses:::: {run_status.model_dump_json(indent=4)}")
                # if self.run.status =
                if run_status.status == "completed":
                    answer = self.process_msgs()
                    print("[INFO] Finished executing query. Sending Answer....")
                    return answer
                elif run_status.status == "requires_action":
                    # Call any function(s) you want here. This method can invoke multiple function calls parallely.
                    print("Call Function Needed......")
                    self.call_required_functions(required_actions=self.run.required_action.submit_tool_outputs.model_dump())
                else:
                    print(f"Run Status:::: {run_status.status}")
                    break

    # -1 (Last)
    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(thread_id=self.thread.id, run_id=self.run.id)
        print(f"Run Steps:::: {run_steps}")

    def get_current_stocks(self, company):
        stocks_api_key = os.environ.get('STOCKS_API_KEY')
        stocksTicker = company
        multiplier = 1
        timespan = "month"
        from_ = "2024-04-20"
        to_ = "2024-05-25"
        limit = 200
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from_}/{to_}?adjusted=true&sort=asc&limit={limit}&apiKey={stocks_api_key}")
        url_2 = (
            f"https://api.polygon.io/v3/reference/tickers?ticker=AAPL&market=stocks&active=true&apiKey={stocks_api_key}")

        try:
            response = requests.get(url)
            if response.status_code == 200:
                # print("RESPONSE:::: ", response.json(), type(response.json()))
                # data = json.dumps(response.json(), indent=4)
                # print("DATA:::: ", data, type(data))
                stocks = response.json()
                # ticker = stocks["ticker"]
                # results = stocks["results"]  # List
                # status = stocks["status"]
                # request_id = stocks["request_id"]
                return stocks
            else:
                return []

        except requests.exceptions.RequestException as e:
            print("Get current stocks exception: ", e)



    


