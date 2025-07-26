from dotenv import load_dotenv
import os
load_dotenv()

# ----- CONFIGURATION -----
# Azure "EnC-Intl-Engg-Subs" Subscription 
DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_ACCESS_TOKEN = os.getenv("DATABRICKS_ACCESS_TOKEN")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
EIA_API_KEY = os.getenv("EIA_API_KEY")

CHAT_COMPLETIONS_PROJECT_ENDPOINT = os.getenv("CHAT_COMPLETIONS_PROJECT_ENDPOINT")
CHAT_COMPLETIONS_MODEL_DEPLOYMENT = os.getenv("CHAT_COMPLETIONS_MODEL_DEPLOYMENT")
CHAT_COMPLETIONS_SUBSCRIPTION_KEY = os.getenv("CHAT_COMPLETIONS_SUBSCRIPTION_KEY")
CHAT_COMPLETIONS_API_VERSION = os.getenv("CHAT_COMPLETIONS_API_VERSION")


orchestrator_agent_name= "AgentsOrchestrator"
fornt_office_agent_name = "FrontOfficeAgent"
back_office_agent_name = "BackOfficeAgent"
middle_office_agent_name = "MiddleOfficeAgent"

#orchestrator_instruction = "You are an AI-powered agent for front, middle, and back offices. Your primary goal is to assist users by leveraging available tools and providing structured, concise, and professional responses. When the user provides an uploaded file and asks for analysis, summary, or insights from it, you MUST call the 'get_insights_from_text' tool and pass the *entire content of the uploaded file* as the 'text_content' argument to that tool.Otherwise, respond to their queries, adapting your style based on the provided behavior mode, and use clear markdown formatting for readability."
# orchestrator_instruction = """You are an AI-powered agent for front, middle, and back offices. Your primary goal is to assist users by leveraging available tools and providing structured, concise, and professional responses.
# **Your responses are strictly limited by the data accessible through your tools.** If a request for detailed information cannot be fully met due to data limitations, clearly state what information is missing and what would be needed to provide a complete answer.
# When the user provides an uploaded file and asks for analysis, summary, or insights from it, you MUST call the 'get_insights_from_text' tool and pass the *entire content of the uploaded file* as the 'text_content' argument to that tool.
# Always remember and utilize the context of the ongoing conversation and any previously provided information (including uploaded files) when formulating your responses, especially for follow-up questions.
# Adapt your style based on the provided behavior mode, and always use clear markdown formatting for readability."""

#orchestrator_instruction = "You are a helpful assistant with expertise in gas and oil trading. you are a helpful front office assistant with expertise in gas trading. Use price data, Delta Lake tables, and ICE exchange data to answer queries. Prioritize recent prices, flag anomalies, and summarize trade impact concisely. Use `get_deals_data` when the user asks about deal volumes, prices, trade counts, or PnL. Use `get_ice_data_simulated` when user asks about ICE exchange prices or spot rates. If information is not available, say Data not available."
orchestrator_instruction = "You are a helpful assistant with expertise in gas and oil trading. you are a helpful front office assistant with expertise in gas trading. Use price data, Delta Lake tables, and ICE exchange data to answer queries. Prioritize recent prices, flag anomalies, and summarize trade impact concisely." \
"Use `get_deals_data` when the user asks about deal volumes, prices, trade counts, or PnL. " \
"Use `generate_deals_chart' when user asks about generating deals graph or chart. " \
"If information is not available, say Data not available."

front_office_instruction = "You are a helpful assistant with expertise in gas and oil trading. you are a helpful front office assistant with expertise in gas trading. Use price data, Delta Lake tables, and ICE exchange data to answer queries. Prioritize recent prices, flag anomalies, and summarize trade impact concisely. Use `get_deals_data` when the user asks about deal volumes, prices, trade counts, or PnL. Use `get_ice_data_simulated` when user asks about ICE exchange prices or spot rates. If information is not available, say Data not available."
middle_office_instruction = "You are a helpful assistant with expertise in gas and oil trading. you are a helpful middle office assistant with expertise in gas trading. Use price data, Delta Lake tables, and ICE exchange data to answer queries. Prioritize recent prices, flag anomalies, and summarize trade impact concisely. Use `get_deals_data` when the user asks about deal volumes, prices, trade counts, or PnL. Use `get_ice_data_simulated` when user asks about ICE exchange prices or spot rates. If information is not available, say Data not available."
back_office_instruction = "You are a helpful assistant with expertise in gas and oil trading. you are a helpful back office assistant with expertise in gas trading. Use price data, Delta Lake tables, and ICE exchange data to answer queries. Prioritize recent prices, flag anomalies, and summarize trade impact concisely. Use `get_deals_data` when the user asks about deal volumes, prices, trade counts, or PnL. Use `get_ice_data_simulated` when user asks about ICE exchange prices or spot rates. If information is not available, say Data not available."

# Define specific instructions for each agent behavior mode
agent_behavior_instructions = {
    "Short Answer": "Give a very brief and to-the-point answer.",
    "Balanced": "Answer clearly and concisely with key insights.",
    "Detailed": "Provide a comprehensive and detailed analysis with all supporting reasoning.",
    "Structured": "Provide your answer in a highly structured format, using markdown headings, bullet points, and numbered lists where appropriate to organize information clearly."
}


graphquery =  f"""
WITH header_leg AS (
  SELECT
    h.deal_num,
    h.tran_num,
    l.deal_leg,
    h.counterparty,
    h.trade_date,
    h.trader,
    h.reval_type AS deal_type,
    h.ins_type AS instrument_type,
    h.trade_status,
    h.trade_currency,
    h.trade_price,
    h.contractual_volume,
    l.commodity,
    l.currency AS leg_currency,
    l.volume_unit,
    l.pay_receive,
    l.location,
    l.price_formula,
    l.proj_curve,
    l.settlement_type AS leg_settlement_type,
    l.quantity_type
  FROM trade_catalog.poc_schema.entity_trade_header h
  LEFT JOIN trade_catalog.poc_schema.entity_trade_leg l
    ON h.deal_num = l.deal_num
    AND h.tran_num = l.tran_num
),

trade_profile AS (
  SELECT
    p.deal_num,
    p.tran_num,
    p.deal_leg,
    p.profile_id,
    p.profile_start_date,
    p.profile_end_date,
    p.payment_date AS profile_payment_date,
    p.notional_volume,
    p.reval_type AS profile_reval_type,
    p.eod_date AS profile_eod_date
  FROM trade_catalog.poc_schema.entity_trade_profile p
)

SELECT
  hl.deal_num,
  COUNT(DISTINCT hl.tran_num) AS transaction_count,
  COUNT(DISTINCT hl.deal_leg) AS leg_count,
  MAX(hl.trade_date) AS latest_trade_date,
  MAX(hl.counterparty) AS counterparty,
  MAX(hl.trader) AS trader,
  MAX(hl.deal_type) AS deal_type,
  MAX(hl.instrument_type) AS instrument_type,
  MAX(hl.trade_status) AS trade_status,
  SUM(hl.contractual_volume) AS total_quantity,
  
  -- PnL Aggregations
  SUM(pd.ltd_realized_value) AS total_realized_pnl,
  SUM(pd.ltd_unrealized_value) AS total_unrealized_pnl,
  SUM(pd.ltd_realized_value + pd.ltd_unrealized_value) AS total_pnl,
  AVG(pd.price) AS avg_price,  -- Changed from pnl_price to price
  SUM(pd.pymt) AS total_payment_value,
  COUNT(DISTINCT pd.cashflow_type) AS cashflow_type_count
FROM header_leg hl
LEFT JOIN trade_profile tp
  ON hl.deal_num = tp.deal_num
  AND hl.tran_num = tp.tran_num
  AND hl.deal_leg = tp.deal_leg
LEFT JOIN trade_catalog.poc_schema.entity_pnl_detail pd
  ON hl.deal_num = pd.deal_num
  AND hl.tran_num = pd.tran_num
  AND hl.deal_leg = pd.deal_leg
  AND tp.profile_id = pd.profile_seq_num
GROUP BY hl.deal_num
ORDER BY hl.deal_num;
"""

query = f"""
WITH header_leg AS (
  SELECT
    h.deal_num,
    h.tran_num,
    l.deal_leg,
    h.counterparty,
    h.trade_date,
    h.trader,
    h.reval_type AS deal_type,
    h.ins_type AS instrument_type,
    h.trade_status,
    h.trade_currency,
    h.trade_price,
    h.contractual_volume, -- Using contractual_volume from header instead of quantity
    l.commodity,
    l.currency AS leg_currency,
    l.volume_unit,
    l.pay_receive,
    l.location,
    l.price_formula,
    l.proj_curve,
    l.settlement_type AS leg_settlement_type,
    l.quantity_type -- Using quantity_type from leg instead of quantity
  FROM trade_catalog.poc_schema.entity_trade_header h
  LEFT JOIN trade_catalog.poc_schema.entity_trade_leg l
    ON h.deal_num = l.deal_num
    AND h.tran_num = l.tran_num
),

trade_profile AS (
  SELECT
    p.deal_num,
    p.tran_num,
    p.deal_leg,
    p.profile_id,
    p.profile_start_date,
    p.profile_end_date,
    p.payment_date AS profile_payment_date,
    p.notional_volume,
    p.reval_type AS profile_reval_type,
    p.eod_date AS profile_eod_date
  FROM trade_catalog.poc_schema.entity_trade_profile p
)

SELECT
  hl.deal_num,
  hl.tran_num,
  hl.deal_leg,
  hl.counterparty,
  hl.trade_date,
  hl.trader,
  hl.deal_type,
  hl.instrument_type,
  hl.trade_status,
  hl.trade_price,
  hl.contractual_volume AS quantity, -- Renamed for consistency
  hl.quantity_type,
  
  -- Trade Profile Details
  tp.profile_id,
  tp.profile_start_date,
  tp.profile_end_date,
  tp.notional_volume,
  
  -- Trade Leg Details
  hl.commodity,
  hl.leg_currency,
  hl.volume_unit,
  hl.pay_receive,
  hl.location,
  hl.price_formula,
  hl.proj_curve,
  
  -- PnL Details
  pd.cashflow_type,
  pd.pnl_start_date,
  pd.pnl_end_date,
  pd.payment_date,
  pd.currency AS pnl_currency,
  pd.volume AS pnl_volume,
  pd.price AS pnl_price,
  pd.pymt,
  pd.df,
  pd.ltd_realized_value,
  pd.ltd_unrealized_value
FROM header_leg hl
LEFT JOIN trade_profile tp
  ON hl.deal_num = tp.deal_num
  AND hl.tran_num = tp.tran_num
  AND hl.deal_leg = tp.deal_leg
LEFT JOIN trade_catalog.poc_schema.entity_pnl_detail pd
  ON hl.deal_num = pd.deal_num
  AND hl.tran_num = pd.tran_num
  AND hl.deal_leg = pd.deal_leg
  AND tp.profile_id = pd.profile_seq_num
"""
