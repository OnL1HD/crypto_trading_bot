# Crypto Trading Bot

This repository contains a prototype cryptocurrency trading system built around one clear idea: turn live market data into readable model decisions, trading signals, and monitored demo-execution behavior.

The project focuses on `BTCUSDT` on the `15m` timeframe and was developed as a system prototype rather than a public trading product.

## What this project is

- a market-data and forecasting pipeline
- a signal and strategy decision prototype
- a demo-trading execution workflow with logging and monitoring
- a dashboard for viewing system state, predictions, signals, and trade activity

## What it does

At a high level, the system follows this flow:

1. market data is collected and prepared
2. the model produces a directional prediction
3. that prediction is converted into a signal
4. the strategy and risk layers decide whether action is allowed
5. demo execution and position tracking are recorded locally
6. the dashboard presents the latest state of the system

## Main parts of the repository

- `src/` - backend application logic, API routes, services, and exchange integrations
- `frontend/` - web dashboard interface
- `scripts/` - data preparation and pipeline helper scripts
- `data/` - local datasets, feature artifacts, signal history, execution logs, and other runtime outputs
- `artifacts/` - saved model artifacts
- `reports/` - generated result summaries and analysis outputs
- `config/` - project configuration

## Current scope

- exchange: Bybit
- market: BTCUSDT
- timeframe: 15-minute candles
- execution mode: demo-only
- purpose: research and system prototyping

## Important notes

- This is not a production trading platform.
- It is not intended as a plug-and-play tool for third-party live trading.
- The repository is meant to show the structure and results of the system, not to provide financial advice.
- Any execution features are limited to controlled demo-trading workflows.

## Project status

The repository already includes:

- collected and processed market data
- feature-generation and model-runtime components
- signal, strategy, risk, and execution history tracking
- a frontend dashboard for inspecting system behavior
- result reports from previous runs

## In plain terms

This project is best understood as a full prototype of an algorithmic trading system: not just a model, and not just a dashboard, but the whole chain from data to decision to monitored demo execution.
