# backend/app/tools.py
import json
import re
from datetime import datetime, date
from typing import Dict, List
import logging
import traceback
from .graph_service import GraphService

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Create console handler with higher level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def generate_graph_from_prompt(prompt: str) -> Dict:
    """Ensure consistent output format for frontend"""
    logger.info("Starting generate_graph_from_prompt tool")
    
    try:
        result = GraphService.generate_from_prompt(prompt)
        if result.get("status") == "success":
            return {
                "status": "success",
                "graph_data": {
                    "type": result["graph"]["type"],
                    "labels": result["graph"]["labels"],
                    "values": result["graph"]["values"],
                    "dataset_label": result["graph"]["dataset_label"],
                    "title": result["graph"]["title"]
                }
            }

        if result.get("status") != "success":
            error_msg = result.get("message", "Unknown error generating graph")
            available_cols = result.get("available_columns", [])
            
            if available_cols:
                error_msg += f"\n\nAvailable columns: {', '.join(available_cols)}"
                
            return {
                "status": "error",
                "message": error_msg,
                "details": result.get("details"),
                "is_error": True
            }
        
        return {
            "status": "success",
            "response": "Here's the requested graph:",
            "graph_data": result["graph"],
            "type": "graph"
        }
        
    except Exception as e:
        logger.error(f"Error in generate_graph_from_prompt tool: {str(e)}")
        return {
            "status": "error",
            "message": f"Graph generation failed: {str(e)}",
            "details": traceback.format_exc(),
            "is_error": True
        }


def get_insights_from_text(text_content: str) -> Dict:
    """
    Get meaningful insights from text content using the agent model.
    This should analyze and summarize the key points from the text.
    """
    logger.info("Starting get_insights_from_text tool")
    
    if not text_content:
        logger.warning("Empty content provided to get_insights_from_text")
        return {
            "status": "error",
            "message": "No content provided"
        }

    try:
        # Import AgentFactory here to avoid circular imports
        from .agentfactory import AgentFactory
        
        # Initialize agent factory
        factory = AgentFactory()
        
        # Create a prompt that asks the agent to analyze the text
        analysis_prompt = f"""
        Analyze the following text and provide key insights, summaries, and important findings.
        Focus on identifying:
        - Main topics and themes
        - Key statistics or numerical data
        - Important names, dates, or entities
        - Any notable trends or patterns
        
        Text to analyze:
        {text_content}
        
        Provide your analysis in a structured JSON format with these sections:
        - summary (brief overall summary)
        - key_points (bulleted list of main points)
        - notable_data (any important numbers or metrics)
        - entities (important people, organizations, or locations mentioned)
        """
        
        logger.debug(f"Sending analysis prompt to agent: {analysis_prompt[:200]}...")
        
        # Get response from agent
        response = factory.process_request2(
            prompt=analysis_prompt,
            agent_mode="Detailed"  # Use detailed mode for comprehensive analysis
        )
        
        if response.is_error:
            logger.error(f"Agent failed to analyze text: {response.response}")
            return {
                "status": "error",
                "message": "Failed to analyze text",
                "details": response.response
            }
        
        logger.info("Successfully generated insights from text")
        return {
            "status": "success",
            "insights": {
                "agent_response": response.response,
                "structured_analysis": _extract_structured_insights(response.response)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_insights_from_text: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Analysis failed: {str(e)}",
            "details": traceback.format_exc()
        }

def _extract_structured_insights(agent_response: str) -> dict:
    """
    Helper function to extract structured insights from agent's text response.
    Attempts to parse JSON if present, otherwise structures the raw response.
    """
    logger.debug("Attempting to extract structured insights from agent response")
    
    try:
        # First try to find JSON in the response
        json_match = re.search(r'```json\n(.+?)\n```', agent_response, re.DOTALL)
        if json_match:
            logger.debug("Found JSON in agent response")
            return json.loads(json_match.group(1))
        
        # If no JSON, try to parse as raw text
        logger.debug("No JSON found, structuring raw response")
        return {
            "summary": agent_response.split("\n")[0] if "\n" in agent_response else agent_response,
            "key_points": [line.strip() for line in agent_response.split("\n") if line.strip()],
            "source": "agent_analysis"
        }
    except Exception as e:
        logger.warning(f"Could not fully structure insights: {str(e)}")
        return {
            "raw_response": agent_response,
            "error": "Could not fully structure insights"
        }

def execute_databricks_query(sql_query: str) -> Dict:
    logger.info("Inside execute_databricks_query Starting execute_databricks_query tool")
    try:
        result = GraphService.execute_sql_query(sql_query)
        if result.get("status") == "success":
            logger.info(f"Query executed successfully. Returned {result.get('row_count', 0)} rows")
        else:
            logger.error(f"Query execution failed: {result.get('message')}")
        return result
    except Exception as e:
        logger.error(f"Error in execute_databricks_query tool: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Tool execution failed: {str(e)}",
            "details": traceback.format_exc()
        }

# Maintain empty user_functions dict as expected by agentfactory.py
user_functions = {}