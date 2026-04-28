import json
from typing import Dict, Type
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import ConfigDict, Field

from cat import AgenticWorkflowConfig, AgenticWorkflowOutput
from cat.services.factory.agentic_workflow import BaseAgenticWorkflowHandler


class ReActAgentWorkflow(BaseAgenticWorkflowHandler):
    """
    ReAct Agent is a specialized agent plugin for Cheshire Cat AI that implements the ReAct (Reasoning and Acting)
    methodology. This agent combines reasoning capabilities with action execution, allowing the Cat to think through
    problems step-by-step while using available tools to solve complex tasks.

    🎯 What is ReAct?
    ReAct (Reasoning and Acting) is a paradigm that interleaves reasoning traces and task-specific actions, enabling the
    agent to:
    - Reason about the current situation and plan the next steps
    - Act by executing tools and procedures
    - Observe the results and adjust the approach accordingly

    ✨ Key Features
    🧠 Step-by-Step Reasoning: Agent thinks through problems methodically before acting
    🔄 Iterative Problem Solving: Continuously refines approach based on results
    ⚡ Tool Integration: Seamlessly executes available procedures and tools
    📝 Memory Integration: Accesses both episodic and declarative memory
    🎛️ Configurable Limits: Adjustable iteration and procedure call limits
    💬 Real-time Feedback: Sends intermediate results during processing

    Therefore, ReActAgent is an implementation of the ReAct agentic workflow. It uses a language model to generate
    actions and react to observations.
    """
    def __init__(self, system_prompt, max_iterations, max_procedures_calls, metadata: Dict | None = None):
        super().__init__(metadata)
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.max_procedures_calls = max_procedures_calls

        if self.max_procedures_calls < 1:
            raise ValueError("max_procedures_calls must be greater than 0")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be greater than 0")

    async def _run_no_tool_binding(self, prompt: ChatPromptTemplate) -> AgenticWorkflowOutput:
        prompt_variables = self._task.prompt_variables or {}

        chain = prompt | self._llm
        langchain_msg = await chain.ainvoke(prompt_variables, config=RunnableConfig(callbacks=self._callbacks))

        output = getattr(langchain_msg, "content", str(langchain_msg))
        return AgenticWorkflowOutput(output=self._clean_response(output))

    async def _run_tool_binding(self, prompt: ChatPromptTemplate) -> AgenticWorkflowOutput:
        tools_map = {t.name: t for t in (self._task.tools or [])}

        # Build a human-readable description of available tools
        tools_description = "\n".join(
            f"- {t.name}: {t.description}" for t in (self._task.tools or [])
        )

        # ReAct instructions injected into the system message
        react_instructions = (
            f"\n\nYou have access to the following tools:\n{tools_description}\n\n"
            "To invoke a tool, respond with exactly:\n"
            "<action>tool_name</action><input>tool_input</input>\n\n"
            "When you are ready to give your final answer, respond with exactly:\n"
            "<answer>your_final_answer</answer>"
        )

        # Format the base prompt using prompt_variables (resolves {context}, etc.)
        prompt_variables = self._task.prompt_variables or {}
        messages = prompt.format_messages(**prompt_variables)

        # Inject ReAct instructions into the existing system message, or prepend one
        if messages and messages[0].type == "system":
            messages[0] = SystemMessage(content=messages[0].content + react_instructions)
        else:
            messages.insert(0, SystemMessage(content=self.system_prompt + react_instructions))

        intermediate_steps = []
        procedure_calls_count = 0
        last_response = ""

        for _ in range(self.max_iterations):
            langchain_msg = await self._llm.ainvoke(messages, config=RunnableConfig(callbacks=self._callbacks))
            last_response = getattr(langchain_msg, "content", str(langchain_msg))

            # Final answer found — return immediately
            if "<answer>" in last_response:
                return AgenticWorkflowOutput(
                    output=self._clean_response(last_response),
                    intermediate_steps=intermediate_steps,
                )

            # Tool call found
            if "<action>" in last_response and "<input>" in last_response:
                if procedure_calls_count >= self.max_procedures_calls:
                    # Procedure-call budget exhausted — stop and return what we have
                    break

                try:
                    tool_name = last_response[
                        last_response.index("<action>") + len("<action>"):last_response.index("</action>")
                    ].strip()
                    tool_input_str = last_response[
                        last_response.index("<input>") + len("<input>"):last_response.index("</input>")
                    ].strip()
                except ValueError:
                    # Malformed tags — stop the loop
                    break

                # Try to parse tool input as JSON (structured tools), fall back to plain string
                try:
                    tool_input = json.loads(tool_input_str)
                except (json.JSONDecodeError, ValueError):
                    tool_input = tool_input_str

                tool = tools_map.get(tool_name)
                if tool:
                    try:
                        observation = await tool.ainvoke(tool_input)
                        procedure_calls_count += 1
                        # Record the step in the format expected by AgenticWorkflowOutput
                        intermediate_steps.append(
                            ((tool_name, {"input": tool_input_str}, {}), str(observation))
                        )
                    except Exception as e:
                        observation = f"Error calling tool '{tool_name}': {e}"
                else:
                    observation = (
                        f"Tool '{tool_name}' not found. "
                        f"Available tools: {list(tools_map.keys())}"
                    )

                # Append the model turn and the tool observation to the running conversation
                messages.append(AIMessage(content=last_response))
                messages.append(HumanMessage(content=f"Observation: {observation}\nContinue your reasoning."))
            else:
                # LLM produced neither an action nor a final answer — stop
                break

        # max_iterations reached, or loop broken — return the last LLM response
        return AgenticWorkflowOutput(
            output=self._clean_response(last_response),
            intermediate_steps=intermediate_steps,
        )


class ReActAgentConfig(AgenticWorkflowConfig):
    system_prompt: str = Field(
        default="You are a helpful agent. Use the available tools to assist the user in fulfilling their request.",
        description="The system prompt that guides the agent's behavior.",
    )
    max_iterations: int = Field(
        default=5,
        description="Maximum number of iterations to run the agent.",
    )
    max_procedures_calls: int = Field(
        default=10,
        description="Maximum number of procedure calls allowed per iteration.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "humanReadableName": "ReAct Agentic Workflow",
            "description": "An agentic workflow that uses a language model to generate actions and react to observations. The agent expects the LLM response to be in the following format: <action>tool_name</action><input>tool_input</input><answer>agent_answer</answer>. The agent will parse the response and execute the tool calls accordingly.",
            "link": "",
        }
    )

    @classmethod
    def pyclass(cls) -> Type[ReActAgentWorkflow]:
        return ReActAgentWorkflow
