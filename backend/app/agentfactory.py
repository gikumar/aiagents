# agentfactory.py
import uuid
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .tools import get_deals_data, generate_deals_chart, get_insights_from_text
from .config import agent_behavior_instructions
import pandas as pd

@dataclass
class AgentResponse:
    response: str
    thread_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    graph_data: Optional[Dict[str, Any]] = None
    is_error: bool = False

class AgentFactory:
    def __init__(self):
        self.threads = {}
        self.agent_modes = {
            "Balanced": {"max_tokens": 5000, "temperature": 0.7},
            "Short": {"max_tokens": 1000, "temperature": 0.5},
            "Detailed": {"max_tokens": 3000, "temperature": 0.8},
            "Structured": {"max_tokens": 4000, "temperature": 0.6}
        }

    # Agent thread id
    def _generate_thread_id(self) -> str:
        """Generates a unique thread ID."""
        #return str("uuid.uuid4()")
        return str("To be fixed")


    # check if prompt is a query about any entity like "deal", "deals", "trade", "pnl", "volume", "counterparty", "realized value"]
    def _is_deal_query(self, prompt: str) -> bool:
        """
        Simple check to see if the prompt is asking about deals.
        Keywords can be expanded for more robust checking.
        """
        deal_keywords = ["deal", "deals", "trade", "pnl", "volume", "counterparty", "realized value"]
        return any(keyword in prompt.lower() for keyword in deal_keywords)

    # Is it a uploade file anlysis request.
    def _handle_file_analysis(self, prompt: str, file_content: str, agent_mode: str, thread_id: str) -> AgentResponse:
        """Handles analysis of an uploaded file."""
        
        analysis_type = "summary" # default
        if "key points" in prompt.lower():
            analysis_type = "key_points"
        elif "detailed" in prompt.lower():
            analysis_type = "detailed"
            
        insights = get_insights_from_text(text_content=file_content, analysis_type=analysis_type)
        return AgentResponse(
            response=insights,
            thread_id=thread_id,
            input_tokens=len(file_content.split()),
            output_tokens=len(insights.split()) if insights else 0
        )

    # for handling all types of graphs request in prompt
    def _handle_deals_graph(self, prompt: str, graph_type: str, agent_mode: str, thread_id: str) -> AgentResponse:
        """Handles a request to generate a graph from deals data."""
        
        graph_data = generate_deals_chart(chart_type=graph_type)
        
        if "error" in graph_data:
            return AgentResponse(
            response=f"Error generating graph: {graph_data['error']}", 
            thread_id=thread_id, 
            is_error=True
        )
    
        # Ensure the graph data is properly structured
        if not isinstance(graph_data, dict) or 'type' not in graph_data:
            return AgentResponse(
                response="Invalid graph data format received from the server",
                thread_id=thread_id,
                is_error=True
            )
        
        response_text = f"Here is the {graph_type} chart showing realized values by deal."
        
        return AgentResponse(
            response=response_text,
            thread_id=thread_id,
            graph_data=graph_data,
            input_tokens=len(prompt.split()),
            output_tokens=len(response_text.split())
        )
    
    

    def _handle_deal_query(self, prompt: str, agent_mode: str, thread_id: str) -> AgentResponse:
        """Handles a general query about deals data by answering the user's question using the data."""
        deals_data = get_deals_data()
        if "error" in deals_data:
            return AgentResponse(response=f"Error fetching deals data: {deals_data['error']}", thread_id=thread_id, is_error=True)
        
        df = pd.DataFrame(deals_data["data"])
        if df.empty:
            return AgentResponse(response="I couldn't find any deal data to analyze.", thread_id=thread_id)

        # Use the LLM to answer the user's question based on the retrieved data.
        prompt_for_llm = f"""
        You are a helpful trading assistant. Based on the data provided below, please answer the user's question.

        User's question: "{prompt}"

        Available data:
        {df.to_string()}

        Your answer:
        """
        
        # Using "detailed" analysis type to encourage a direct and comprehensive answer.
        response_text = get_insights_from_text(text_content=prompt_for_llm, analysis_type="detailed")

        return AgentResponse(
            response=response_text,
            thread_id=thread_id,
            input_tokens=len(prompt_for_llm.split()),
            output_tokens=len(response_text.split())
        )
        
    def _generate_text_response(self, prompt: str, agent_mode: str, chat_history: Optional[list]) -> str:
        """Generates a text-based response using the LLM for general queries."""
        full_context = ""
        if chat_history:
            for msg in chat_history:
                full_context += f"{msg['role']}: {msg['content']}\n"
        full_context += f"user: {prompt}"

        # Using the existing tool for a generic response
        return get_insights_from_text(text_content=full_context, analysis_type="summary")

    # --- End of Helper Methods ---

    def process_request(self,
                       prompt: str,
                       agent_mode: str = "Balanced",
                       file_content: Optional[str] = None,
                       chat_history: Optional[list] = None,
                       is_graph_request: bool = False,
                       graph_type: str = "bar") -> AgentResponse:
        """
        Process user request and generate appropriate response
        """
        thread_id = self._generate_thread_id()
        
        try:
            # Route to file analysis if a file is provided with analysis keywords
            if file_content and ("analyze" in prompt.lower() or "insight" in prompt.lower() or "summary" in prompt.lower()):
                return self._handle_file_analysis(prompt, file_content, agent_mode, thread_id)


            # Route to graph generation if explicitly requested or implied
            is_graph_implied = "graph" in prompt.lower() or "chart" in prompt.lower() or "plot" in prompt.lower()
            if is_graph_request or (self._is_deal_query(prompt) and is_graph_implied):
                 return self._handle_deals_graph(prompt, graph_type, agent_mode, thread_id)


            # Route to deal data query for text response
            if self._is_deal_query(prompt):
                return self._handle_deal_query(prompt, agent_mode, thread_id)
            

            # Fallback to a general text response for any other query
            response_text = self._generate_text_response(prompt, agent_mode, chat_history)
            
            
            return AgentResponse(
                response=response_text,
                thread_id=thread_id,
                input_tokens=len(prompt.split()),
                output_tokens=len(response_text.split())
            )

        except Exception as e:
            # Log the full error for debugging
            print(f"Error processing request: {e}\n{traceback.format_exc()}")
            return AgentResponse(
                response=f"An unexpected error occurred. Please check the server logs for details.",
                thread_id=thread_id,
                is_error=True
            )
