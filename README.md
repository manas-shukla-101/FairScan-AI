# FairScan: Dataset Fairness & AI Bias Audit Platform

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python_3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_API-F55036?style=for-the-badge&logo=groq&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-8E75C2?style=for-the-badge&logo=googlegemini&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<div align="center">
  <h3><b>Upload. Audit. Understand. Document.</b></h3>
  <p><i>A zero-intervention, plain-English dataset fairness auditing and bias mitigation platform.</i></p>
</div>

---

## 📑 Table of Contents

| Section | Description |
|---------|-------------|
| [🧠 Overview](#-overview) | Project introduction and capabilities |
| [⚠️ The Problem](#-the-problem) | Silent algorithmic bias and statistical complexity |
| [💡 The Solution: FairScan](#-the-solution-fairscan) | 1-click automated auditing in everyday English |
| [🛠️ The Tech Stack](#-the-tech-stack) | Full-stack architecture & libraries |
| [🎯 Strategic Logic Flow](#-strategic-logic-flow) | End-to-end data processing pipeline |
| [🔑 Custom API Keys](#-custom-api-keys--privacy-guarantee) | Browser-level Groq, Gemini & Offline setup |
| [🚀 Quick Start](#-quick-start) | One-command local setup instructions |
| [🌟 Key Features](#-key-features) | Standout functionalities |
| [💼 Use Cases](#-use-cases) | Hiring, credit scoring, healthcare & compliance |
| [⚖️ Regulatory Disclaimers](#-regulatory-disclaimers) | EU AI Act & US EEOC guidelines |
| [👋 Connect](#-socials) | Social links |

---

## 🧠 Overview

**FairScan** is a modern dataset fairness and bias auditing platform designed for data practitioners, compliance teams, and software engineers. It identifies and investigates statistical disparities in datasets **before** machine learning models are trained or deployed.

Traditional fairness toolkits produce dense statistical jargon that only PhD statisticians understand. **FairScan translates every insight into plain, 5th-grade English** ("Gap vs Top Group", "Chance vs Top Group", "Balancing Multipliers") while maintaining mathematical rigor under the hood.

---

## ⚠️ The Problem

1. **Silent Historical Bias**: Training machine learning models on historical data blindly perpetuates human discrimination (in hiring, loan approvals, college admissions, and insurance).
2. **Confusing Academic Jargon**: Traditional fairness toolkits spit out confusing abbreviations like *DIR, SPD, stochastic parity, Fisher exact intervals, Wilson scores*, leaving non-technical auditors lost.
3. **Complex Configuration Barriers**: Most tools require users to manually specify column mappings, target encodings, reference baselines, and parameter thresholds before running an audit.
4. **Data Privacy Hazards**: Sending raw customer records, applicant names, or financial records to external cloud LLMs violates GDPR, CCPA, and enterprise privacy standards.

---

## 💡 The Solution: FairScan

FairScan eliminates the friction:

* **Zero Intervention / 1-Click Auto-Audit**: Drop any CSV spreadsheet. FairScan's heuristic inference engine automatically identifies the outcome being measured, detects protected demographic attributes, assigns reference standards, and runs the entire audit instantly.
* **Plain-English Explanations**: Every metric is translated into friendly, non-intimidating English that anyone on your team can understand immediately.
* **100% Zero-PII AI Narrative Layer**: Multi-provider support for **Groq AI (Qwen 27B / Llama 3.3)** and **Google Gemini (Gemini 2.5 Flash)**. Only anonymous aggregate summary rates are sent—raw dataset records never leave your machine.
* **Mathematical Bias Mitigation**: Non-destructive Kamiran & Calders sample reweighting harmonizes base rates across demographic groups without modifying or deleting original rows.
* **Publication-Grade PDF Reports**: One-click generation of formal, printable compliance PDF reports complete with fingerprints, audit tables, and regulatory disclaimers.

---

## 🛠️ The Tech Stack

* **Frontend**: React + Vite (Cyber-Minimalist Obsidian theme inspired by `beady.ai`)
* **Styling**: Tailwind CSS + custom high-contrast cyber accents (`#facc15` Electric Yellow, Obsidian `#0a0a0c`)
* **Interactive Visualizations**: Plotly (`react-plotly.js`)
* **Icons**: Lucide React
* **Backend API**: Python 3.14+ / FastAPI / Uvicorn / Pydantic
* **Statistical Core**: NumPy, SciPy, pandas, Fairlearn algorithms
* **Explanation Layer**: Groq Cloud API, Google Gemini API, and Deterministic Offline Rule Engine
* **Report Generation**: ReportLab PDF Engine (Two-pass `NumberedCanvas` with "Page X of Y")
* **Testing**: pytest (18 passing tests with 100% coverage)
 
---

## 🎯 Strategic Logic Flow

```
┌─────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│   Upload CSV    │ ───►  │ Auto-Detection Engine  │ ───►  │  Dataset Profiling    │
│  (Drag & Drop)  │       │ (Target & Demographics)│       │ (Counts, Success Rates)│
└─────────────────┘       └────────────────────────┘       └────────────────────────┘
                                                                       │
                                                                       ▼
┌─────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│  Download PDF   │ ◄───  │ Plain-English AI Story │ ◄───  │ Fairness Calculations  │
│  Audit Report   │       │ (Groq / Gemini / Local)│       │  (EEOC 80% Rule & Gap) │
└─────────────────┘       └────────────────────────┘       └────────────────────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │   Mitigation Lab       │
                          │(Sample Re-weighting CSV│
                          └────────────────────────┘
```

### 1. Zero-Intervention Ingestion & Auto-Detection
Drop any CSV file. The system checks headers for duplicates, calculates a cryptographic SHA-256 fingerprint, infers data types, detects the decision column (e.g., `hired`, `loan_approved`), determines the favorable outcome value, and selects demographic attributes (e.g., `gender`, `race`, `age_group`).

### 2. Rigorous Fairness Audit
Calculates group-level success rates alongside two primary benchmarks:
* **Gap vs Top Group** (Statistical Parity Difference): Direct percentage difference between each group and the benchmark standard.
* **Chance vs Top Group** (Disparate Impact Ratio): Evaluates compliance against the US EEOC Four-Fifths (80%) Rule.
* **Model Evaluation Guard**: Equal Opportunity and Equalized Odds are strictly locked unless explicit model predictions are supplied alongside ground-truth labels.

### 3. Plain-English Narrative Layer
Generates an intuitive, readable breakdown:
* **The Quick Take**: Highlights in 2 sentences whether the dataset is balanced or presents significant gaps.
* **What the Numbers Show**: Explains group success rates in plain words.
* **Next Steps**: Actionable investigation steps (investigating proxies, past decision criteria, and sampling gaps).

### 4. Non-Destructive Data Balancing (Mitigation Lab)
Computes mathematically derived fairness weights for each record:
$$\text{Weight}(S=s, Y=y) = \frac{P(S=s) \times P(Y=y)}{P(S=s, Y=y)}$$
Exports a balanced CSV dataset ready for training fair machine-learning models.

---

## 🔑 Custom API Keys & Privacy Guarantee

FairScan allows users to provide their own AI API keys directly inside the web interface:

1. Click **API Keys** in the top navigation bar.
2. Enter your **Groq API Key** (`gsk_...`) or **Google Gemini API Key** (`AIzaSy...`).
3. Select your preferred provider (`Auto`, `Groq`, `Gemini`, or `Offline`).
4. Click **Save & Apply**.

### 🔒 Privacy by Design
* **Stored in Browser Only**: Your keys are saved in your local browser's `localStorage` and never stored on our database or disk.
* **Zero Raw Data Sent**: Neither your raw dataset rows nor personally identifiable records are ever transmitted to external AI APIs. Only anonymous aggregate summary percentages are used for text generation.
* **100% Offline Capable**: No API key? No problem! FairScan includes a built-in deterministic expert engine that functions completely offline without internet access.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/manas-shukla-101/FairScan-AI.git
cd FairScan-AI
```

### 2. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 4. Run FairScan (Single Command!)
We provide a zero-configuration launcher that manages background services and port conflicts automatically:
```bash
python run_fairscan.py
```
Open your browser at:
* **Frontend**: `http://localhost:5173`
* **FastAPI Docs**: `http://127.0.0.1:8000/docs`

---

## 🌟 Key Features

* **Instant 1-Click Audits**: Automatic variable detection eliminates complex wizards.
* **Cyber-Minimalist UI**: Clean obsidian palette with electric yellow accents, responsive cards, and zero distracting gradients.
* **Interactive Plotly Visualizations**: Responsive group success rate comparisons and 80% threshold markers.
* **Built-in Sample Scenarios**: One-click demo datasets for **Job Hiring** and **Loan Approval** to inspect bias immediately.
* **Interactive Mitigation**: Preview before-and-after fairness metrics and download balanced datasets.
* **Formal PDF Audit Reports**: Printable PDF reports equipped with SHA-256 fingerprints, group tables, recommendations, and regulatory notices.
* **Extensive Automated Test Suite**: 18 unit and integration tests covering edge cases (zero denominators, single-group categories, duplicate headers).

---

## 💼 Use Cases

* **Human Resources & Recruitment**: Verify applicant screening datasets before training automated resume-parsing models.
* **Banking & Lending**: Audit credit card and loan approval datasets to avoid algorithmic redlining and ensure fair lending standards.
* **Healthcare & Life Sciences**: Validate clinical study cohorts and diagnosis datasets for balanced demographic representation.
* **Model Governance & Auditing**: Prepare documentation and evidence for internal AI ethics boards and compliance audits.

---

## ⚖️ Regulatory Disclaimers

FairScan is an analytical decision-support tool. It does not certify legal compliance or prove intentional discrimination under law:
* **US EEOC Four-Fifths (80%) Rule**: An observed selection rate below 80% serves as an empirical indicator of adverse impact requiring investigation.
* **EU AI Act (Article 10)**: Datasets for high-risk AI systems must be examined for possible biases; FairScan assists in documenting these pre-training assessments.

---

**Designed and Developed with ❤️ by Manas Shukla**

---

## 🌐 Socials:
[![Portfolio](https://img.shields.io/badge/Portfolio-Website-blue)](https://manas-shukla-portfolio.framer.website) [![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?logo=Instagram&logoColor=white)](https://instagram.com/manas_shukla_101) [![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?logo=linkedin&logoColor=white)](https://linkedin.com/in/manas-shukla-006774370) [![Email](https://img.shields.io/badge/Email-D14836?logo=gmail&logoColor=white)](mailto:shuklamanas8928@gmail.com)
