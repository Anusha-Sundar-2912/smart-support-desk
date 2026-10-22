# Smart Support Desk

### Salesforce-Powered Customer Support Intelligence & Case Management

An end-to-end customer support intelligence application built with **Salesforce Lightning Web Components (LWC), Apex, Salesforce Flow, FastAPI, and PostgreSQL**.

Smart Support Desk analyzes real e-commerce transactions and customer reviews to identify potential support issues, prioritize cases, investigate order histories, and integrate support workflows with Salesforce Service Cloud capabilities.

The project demonstrates Salesforce development, REST API integration, asynchronous processing, data-driven classification, and workflow automation using a real-world dataset.

---

## Problem Statement

Large e-commerce marketplaces process thousands of orders, making it difficult for customer support teams to proactively identify delivery failures, negative customer experiences, canceled orders, and potentially unresolved shipments.

Order information, customer reviews, payment details, and delivery records are often distributed across different systems. Support agents must manually investigate these sources before determining which issues require attention.

**Smart Support Desk addresses this problem by integrating marketplace data analysis with Salesforce-based case management and investigation workflows.**

The system identifies potential support issues using historical transaction data, assigns rule-based priorities, provides a unified investigation interface, and supports synchronization into Salesforce Cases.

---

## Key Features

### 1. Support Intelligence Dashboard

An interactive Salesforce Lightning dashboard for monitoring marketplace support concerns.

- Identifies **17,822 potential support issues** from the Olist dataset.
- Classifies **6,324 high-priority** and **11,498 medium-priority** issues.
- Displays six evidence-based issue categories.
- Provides category breakdowns and support metrics.
- Supports searching, filtering, sorting, and paginated results.
- Retrieves marketplace data through Apex-integrated REST APIs.

### 2. Order Investigation Workspace

A centralized investigation interface that allows support agents to examine individual marketplace orders.

- Order status and delivery information
- Customer details and order history
- Customer reviews and ratings
- Purchased products and seller information
- Item prices and freight charges
- Payment methods and transaction details
- On-demand Portuguese-to-English review translation

This reduces the need to investigate customer issues across multiple disconnected datasets.

### 3. Salesforce Case Synchronization

Integrates detected marketplace issues with Salesforce's standard Case object.

- Creates Salesforce Cases from identified marketplace issues.
- Uses **Queueable Apex** for asynchronous processing.
- Processes synchronization requests in batches of up to 20.
- Checks existing order-linked Cases to reduce duplicate creation.
- Assigns Case priorities based on detected issue severity.
- Stores original Olist order and customer identifiers in custom Case fields.
- Makes synchronized records accessible through standard Salesforce Case views.

### 4. High-Priority Follow-Up Automation

Implements a Salesforce record-triggered Flow for high-priority support Cases.

- Configured to execute when a Salesforce Case is created.
- Evaluates the condition `Priority = High`.
- Uses an after-save Create Records action to create a follow-up Task.
- Configures the Task's subject, status, priority, and related Case reference.
- Designed to support automatic investigation follow-ups.

**Implementation status:** The Flow is configured, saved, and active in Salesforce. Successful automatic Task creation for newly synchronized Cases remains to be verified end to end.

### 5. REST API Integration

A Python FastAPI backend provides structured access to marketplace data stored in PostgreSQL.

API capabilities include:

- Support issue discovery and classification
- Aggregate issue metrics
- Order and customer investigation
- Customer review retrieval
- Purchased item and seller details
- Payment information
- Customer order history
- Customer review translation

Salesforce communicates with the backend through **Apex HTTP callouts and a Named Credential**, keeping external API configuration separate from application logic.

### 6. Portuguese-to-English Review Translation

The application supports on-demand translation of Portuguese customer reviews into English.

- Retrieves original customer review text from PostgreSQL.
- Exposes a dedicated FastAPI translation endpoint.
- Integrates with the external **MyMemory Translation API**.
- Displays the English translation alongside the original review in Salesforce.
- Preserves the original customer feedback for reference.

---

## Application Screenshots

### 1. Support Operations Dashboard

![Support Operations Dashboard](https://github.com/user-attachments/assets/3d8cf3b5-aba0-419b-85da-7cd2b2d33851)

Displays 17,822 detected potential support issues, priority distribution, and six issue categories.

### 2. Issue Explorer

![Issue Explorer](https://github.com/user-attachments/assets/38844349-572e-434a-981e-c8086a52f1e0)

Allows agents to search, filter, and investigate marketplace orders by issue category, priority, rating, and status.

### 3. Salesforce Case Management

![Salesforce Case Management](https://github.com/user-attachments/assets/3575dd32-d779-416e-8950-b26846b48d81)

Displays synchronized Salesforce Cases with assigned priorities and source order references.

### 4. Salesforce Record-Triggered Flow

![Salesforce Flow Builder](https://github.com/user-attachments/assets/6eb06ec0-1b07-4449-958e-bbbb906717da)

Shows the active High Priority Case Follow-Up Flow, configured to create follow-up Tasks for newly created high-priority Cases.

### 5. Salesforce Flow Trigger Explorer

![Salesforce Flow Trigger Explorer](https://github.com/user-attachments/assets/2571b483-b7de-42ca-a663-ade6024d6332)

Confirms the high-priority Case Flow is registered and active as an after-save automation.

---

## System Architecture

```text
                   Salesforce Lightning App
                             |
                  Lightning Web Components
                             |
                       Apex Services
                             |
                  Salesforce Named Credential
                             |
                        REST / HTTPS
                             |
                       FastAPI Backend
                             |
                         SQLAlchemy
                             |
                         PostgreSQL
                             |
                  Olist E-Commerce Dataset


                Salesforce Case Management
                             |
                    Queueable Apex
                             |
                     Salesforce Cases
                             |
                  Record-Triggered Flow
                             |
                High-Priority Follow-Up Task
                    (Configured Automation)


                  Review Translation
                             |
                   FastAPI Endpoint
                             |
                 MyMemory Translation API
```

### Architecture Overview

**Frontend:** Lightning Web Components provide the interactive dashboard and investigation interface inside Salesforce.

**Salesforce application layer:** Apex services manage external API communication and asynchronous Case synchronization.

**Backend:** FastAPI implements issue-detection logic, data retrieval, and review translation endpoints.

**Database:** PostgreSQL stores the imported marketplace dataset, with SQLAlchemy handling database access.

**Automation:** Salesforce Flow defines the follow-up workflow for high-priority Case creation.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Salesforce LWC, HTML, CSS, JavaScript |
| Salesforce Development | Apex, SOQL, Queueable Apex |
| Workflow Automation | Salesforce Flow |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Integration | REST APIs, HTTP Callouts, Named Credentials |
| Translation | MyMemory Translation API |
| Testing | Apex Unit Tests, HTTP Callout Mocking |
| Deployment | Salesforce Platform, Render |
| Version Control | Git, GitHub |

---

## Dataset

**Source:** [Brazilian E-Commerce Public Dataset by Olist — Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

The application uses real historical Brazilian marketplace records, including customer orders, reviews, deliveries, payments, and product information.

| Dataset Table | Records |
|---|---:|
| Customers | 99,441 |
| Orders | 99,441 |
| Order Items | 112,650 |
| Payments | 103,886 |
| Reviews | 99,224 |
| Products | 32,951 |
| Sellers | 3,095 |
| Geolocation | 738,332 |
| Category Translations | 71 |

### Issue Detection and Classification

The application identifies potential support concerns across six categories:

| Issue Category | Detected Issues |
|---|---:|
| Low customer rating | 8,325 |
| Late delivery | 2,548 |
| Low rating and late delivery | 3,986 |
| Canceled order | 625 |
| Unavailable order | 609 |
| Potentially overdue order | 1,729 |
| **Total** | **17,822** |

Issue classification is based on recorded order statuses, review ratings, and delivery timestamps.

The system uses **deterministic, rule-based classification**, not a trained machine-learning model.

**Data interpretation:** These records represent potential support issues inferred from historical transactions, not verified customer-submitted support tickets. Potentially overdue orders are evaluated relative to the historical dataset snapshot rather than the current date.

---

## Salesforce Implementation

### Lightning Web Components

The Salesforce frontend provides:

- Support dashboard and issue metrics
- Searchable and filterable issue explorer
- Detailed order investigation
- Customer review and payment information
- Review translation display
- Actions for interacting with synchronized support records

### Apex Services

The Salesforce application includes Apex services responsible for:

- Calling external FastAPI endpoints
- Handling HTTP responses
- Processing marketplace data
- Creating Salesforce Case records
- Running asynchronous synchronization operations

### Salesforce Data Model

The project uses Salesforce's standard **Case** object with custom fields to preserve references to marketplace data.

Examples include:

- Olist Order ID
- Olist Customer ID
- Issue Reason
- Review Rating
- Delivery Delayed

Standard Salesforce fields such as Subject, Status, Priority, and Case Owner support Case management.

### Salesforce Flow

The high-priority follow-up Flow uses:

- **Flow Type:** Record-Triggered Flow
- **Object:** Case
- **Trigger:** Record Created
- **Entry Condition:** Priority Equals High
- **Execution:** After Save
- **Action:** Create Task Record

The Task action is configured to link the follow-up activity to the originating Case.

---

## Testing and Verification

### Verified Functionality

- Salesforce LWC dashboard displays issue metrics retrieved from the backend.
- Issue Explorer supports filtering and investigation of marketplace orders.
- FastAPI endpoints retrieve related customer, review, product, and payment data.
- Salesforce Case synchronization creates Cases containing Olist source identifiers.
- Asynchronous Apex synchronization has completed successfully.
- Portuguese-to-English review translation displays successfully in the Salesforce interface.
- An Apex HTTP callout mock unit test has passed.
- The high-priority Case Flow is configured and active in Salesforce.

### Remaining Validation

- End-to-end verification that the active Flow automatically creates Tasks for newly created high-priority Cases.
- Broader automated testing for Apex synchronization and edge cases.
- Retry and failure-handling scenarios for external integrations.

---

## Deployment

The system uses two deployed application components.

**Salesforce Platform**

Hosts the Lightning application, LWC dashboard, Apex services, Case records, and record-triggered automation.

**Render**

Hosts the FastAPI backend that provides marketplace investigation and issue-detection endpoints.

**Backend URL:** https://smart-support-desk.onrender.com

**API Documentation:** https://smart-support-desk.onrender.com/docs

The Salesforce application requires access to an appropriately configured Salesforce development org.

---

## Project Structure

```text
smart-support-desk/
├── backend/
│   └── ...
├── salesforce/
│   └── force-app/
│       └── main/
│           └── default/
│               ├── classes/
│               └── lwc/
├── scripts/
├── screenshots/
│   ├── 01-support-dashboard.png
│   ├── 02-issue-explorer.png
│   ├── 03-salesforce-cases.png
│   ├── 04-salesforce-flow.png
│   └── 05-flow-trigger-explorer.png
└── requirements.txt
```

---

## Local Development

### Backend Setup

1. Clone the repository.

2. Create and activate a Python virtual environment.

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the backend environment variables required for PostgreSQL and API authentication.

5. Provision PostgreSQL and import the Olist dataset using the project's data preparation and import scripts.

6. Start the FastAPI development server using the backend application's configured entry point.

### Salesforce Setup

1. Install Salesforce CLI and authenticate a development org.
2. Deploy the Salesforce DX project metadata.
3. Configure the Named Credential for the FastAPI backend.
4. Configure the API authentication settings securely.
5. Verify the Lightning application and Apex integration.
6. Review and activate the record-triggered Flow where required.

---

## Future Improvements

- Expand automated Apex and backend integration test coverage.
- Validate and strengthen high-priority Task automation.
- Implement durable synchronization progress tracking.
- Add retry handling and failure recovery for synchronization jobs.
- Introduce configurable Case assignment and escalation rules.
- Improve translation reliability through caching and fallback providers.
- Add more detailed operational monitoring and error reporting.

---
