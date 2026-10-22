
# Smart Support Desk

### Salesforce-Powered Customer Support Intelligence & Case Management

Smart Support Desk is an enterprise-style customer support application built using **Salesforce Lightning Web Components (LWC), Apex, Salesforce Flow, FastAPI, and PostgreSQL**.

The application analyzes real e-commerce order and review data to identify potential customer-support issues, prioritize cases, investigate order histories, and automate follow-up workflows in Salesforce.

## Problem Statement

Large e-commerce marketplaces process thousands of orders, making it difficult for support teams to identify customers experiencing delivery delays, poor experiences, canceled orders, or unresolved shipments.

Customer feedback and operational data often exist in separate systems, requiring agents to manually investigate orders before deciding which issues need attention.

**Smart Support Desk addresses this problem by combining data-driven issue detection with Salesforce case management and workflow automation.**

## Key Features

### 1. Support Intelligence Dashboard

- Displays **17,822 detected potential support issues** from the Olist dataset.
- Provides priority-based metrics and issue-category breakdowns.
- Supports filtering, searching, sorting, and pagination.
- Categorizes issues using order status, delivery performance, and customer ratings.

### 2. Order Investigation Workspace

- Displays order and delivery details.
- Retrieves customer information and order history.
- Shows customer reviews and ratings.
- Displays purchased products, sellers, and freight charges.
- Retrieves payment information.

### 3. Salesforce Case Synchronization

- Converts detected marketplace issues into Salesforce Case records.
- Uses asynchronous Apex Queueable processing.
- Supports paginated synchronization in batches of 20.
- Checks existing order-linked Cases to reduce duplicates.
- Assigns priorities and stores references to source orders.

### 4. Automated High-Priority Follow-Ups

- Uses Salesforce record-triggered Flow.
- Automatically creates follow-up Tasks for high-priority Cases.
- Links Tasks to their corresponding Salesforce Case records.

### 5. REST API Integration

- FastAPI provides endpoints for issue discovery, order investigation, reviews, payments, products, and customer history.
- Apex integrates Salesforce with the external API using a Named Credential.
- PostgreSQL stores and serves the underlying marketplace data.

### 6. Portuguese Review Translation

- Includes an integration for translating Portuguese customer reviews into English.
- Uses a Python translation library through a FastAPI endpoint.

## System Architecture

```text
               Salesforce Lightning App
                         |
             Lightning Web Components
                         |
                 Apex Controllers
                         |
               Salesforce Named Credential
                         |
                  FastAPI REST API
                         |
                     PostgreSQL
                         |
              Olist E-Commerce Dataset

Salesforce Automation:

Detected Issues
      |
      v
Apex Queueable
      |
      v
Salesforce Cases
      |
      v
Record-Triggered Flow
      |
      v
High-Priority Follow-Up Tasks
```

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Salesforce LWC, HTML, CSS, JavaScript |
| Salesforce Backend | Apex, SOQL, Queueable Apex |
| Automation | Salesforce Flow |
| API Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Integration | REST APIs, Salesforce Named Credentials |
| Testing | Apex Unit Testing, HTTP Callout Mocking |
| Deployment | Salesforce Platform, Render |
| Version Control | Git, GitHub |

## Dataset

**Source:** [Brazilian E-Commerce Public Dataset by Olist — Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

The project uses real historical Brazilian marketplace data, including:

| Data | Records |
|---|---:|
| Orders | 99,441 |
| Customers | 99,441 |
| Order Items | 112,650 |
| Payments | 103,886 |
| Reviews | 99,224 |
| Products | 32,951 |
| Sellers | 3,095 |

### Issue Detection

The application identifies potential support issues based on:

- Low customer review ratings
- Late deliveries
- Low ratings combined with late deliveries
- Canceled orders
- Unavailable orders
- Potentially overdue shipments

These are **rule-derived potential issues**, not verified customer-submitted support tickets. The historical dataset is used for demonstration and analysis.

## Project Structure

```text
smart-support-desk/
├── backend/             # FastAPI backend and API routes
├── salesforce/          # Salesforce DX project
│   └── force-app/
│       └── main/
│           └── default/
│               ├── classes/   # Apex services and tests
│               └── lwc/       # Lightning Web Components
├── scripts/             # Data preparation and import utilities
└── requirements.txt     # Python dependencies
```

## Testing and Verification

The following workflows have been verified in the deployed application:

- Dashboard retrieves and displays issue data.
- Order Investigation loads related marketplace records.
- Salesforce Case synchronization creates order-linked Cases.
- Asynchronous synchronization job completes without execution errors.
- High-priority Case Flow creates related follow-up Tasks.
- Apex API service mock test passes (1 test executed, 100% pass rate).

## Deployment

The application consists of two deployed components:

**Salesforce:** Hosts the Lightning application, LWC dashboard, Apex services, Salesforce Cases, and automation.

**Render:** Hosts the FastAPI backend, which communicates with PostgreSQL.

## Local Development

1. Clone the repository.
2. Create a Python virtual environment.
3. Install dependencies using `pip install -r requirements.txt`.
4. Configure the required backend environment variables securely.
5. Provision PostgreSQL and import the Olist dataset using the project's data scripts.
6. Authenticate a Salesforce development org using Salesforce CLI.
7. Deploy the Salesforce metadata using Salesforce CLI.
8. Configure the Salesforce Named Credential to connect securely to the backend.

## Future Improvements

- More comprehensive automated test coverage.
- Durable synchronization progress tracking and retry handling.
- Additional case assignment and escalation rules.
- Improved customer-review translation reliability.

---
