# QueueStorm Investigator

## Source of Truth

The following documents are authoritative.

Read them before every implementation task.

1. docs/QueueStorm_Problem_Analysis.md

2. docs/QueueStorm_Investigator_PRD.md

3. docs/QueueStorm_Investigator_HLD.md

4. docs/SUST_Hackathon_Preli_Problem_Statement.pdf

5. docs/SUST_Preli_Evaluation_Rubric_With_Explanations.pdf

6. docs/SUST_Preli_Team_Instructions_Manual.pdf

7. docs/SUST_Preli_Sample_Cases.json

Never contradict these documents.

If documents conflict,

follow

Problem Statement

↓

Evaluation Rubric

↓

Team Manual

↓

HLD

↓

PRD

↓

Problem Analysis

-------------------------------------

## Coding Philosophy

Always keep the project runnable.

Never generate placeholder code.

Never ignore API schema.

Never simplify architecture without asking.

Never hardcode secrets.

Always validate inputs.

Always write production-quality code.

-------------------------------------

## Architecture

Follow HLD exactly.

Never invent another architecture.

-------------------------------------

## Security

Validate every request.

Never expose secrets.

Never expose stack traces.

Never ask customers for OTP.

Always follow safety rules.

-------------------------------------

## AI

Implement evidence reasoning first.

Classification second.

LLM third.

Safety layer fourth.

-------------------------------------

## Testing

Every milestone should compile.

Health endpoint must always work.

Never break previous milestones.

-------------------------------------

## Before Writing Code

Always read

Problem Analysis

PRD

HLD

again.
