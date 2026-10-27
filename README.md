# MediCard 🩺💳
### A Unified Technical Framework for AI-Driven Global Medical Navigation and Sovereign Identity

[![Domain](https://img.shields.io/badge/Domain-AI%20%2F%20Healthcare%20IT%20%2F%20Fintech-green)]()
[![Status](https://img.shields.io/badge/Status-Prototype%20%2F%20Research-orange)]()

MediCard is an AI-powered healthcare coordination platform designed to eliminate the friction, language barriers, and out-of-pocket delays associated with cross-border medical care[cite: 1, 2]. By combining intelligent provider discovery, HL7 FHIR standardized health records, patient-controlled consent management, and automated financial routing, MediCard creates a seamless bridge between patients and global medical networks[cite: 1, 2, 3].

---

## Key Features

- ** AI Semantic Provider Search:** Goes beyond keyword lookups to match patients with the most relevant hospitals and specialists based on medical intent, location, language preference, and accepted insurance[cite: 2, 4].
- ** Medical Data Interoperability (FHIR & IPS):** Standardizes clinical records into HL7 FHIR R4 and International Patient Summary (IPS) formats using universal clinical vocabularies like **SNOMED CT**, **LOINC**, and **RxNorm**[cite: 1, 4].
- ** Sovereign Digital Identity & Consent:** Gives patients granular control over who accesses their medical information through secure authentication, role-based access, and permissioned audit trails (Hyperledger Fabric prototype)[cite: 1, 2].
- ** Programmatic Financial Routing:** Coordinates insurance pre-authorizations, eligibility checks (X12 EDI 270/271), and single-use Virtual Credit Cards (VCC) locked to healthcare Merchant Category Codes (MCCs)[cite: 2, 5].
- ** OCR-Based Medical Bill Verification:** Automatically extracts line items, pricing, and totals from foreign medical invoices using OCR and validates them against rules to detect discrepancies[cite: 1, 2].

---

## Technology Stack

| Layer | Technologies / Frameworks |
| :--- | :--- |
| **Frontend UI** | React.js |
| **Backend & APIs** | Node.js, Express.js |
| **AI, NLP & Search** | Python, Vector Embeddings (Qdrant / Hybrid Search Engine), Pydantic Parsers[cite: 1, 4] |
| **Database & Storage** | MongoDB |
| **Healthcare Standards** | HL7 FHIR R4, International Patient Summary (IPS), SNOMED CT, LOINC, RxNorm[cite: 1, 4] |
| **Security & Blockchain** | AES-256-GCM Encryption, Hyperledger Fabric (for consent audit logs)[cite: 1, 2] |
| **Financial / OCR** | OCR Libraries, Stripe Issuing / Marqeta / Nium (Virtual Card APIs), X12 EDI[cite: 2, 5] |

---

## System Architecture Overview

MediCard's modular architecture is divided into five core operational layers:
1. **User Interface Layer:** Patient/Provider registration, search dashboards, and status trackers.
2. **AI & Application Services Layer:** Handles semantic provider matching, intent parsing, and OCR invoice extraction[cite: 1, 2, 4].
3. **Healthcare Interoperability Layer:** Manages FHIR/IPS resource mapping and clinical data translation[cite: 1, 4].
4. **Security & Identity Layer:** Enforces authentication, encryption, role-based access control, and consent verification[cite: 1, 2].
5. **Financial Routing Layer:** Coordinates insurance eligibility, automated claims processing, and virtual payment tracking[cite: 1, 2, 5].

---

### **Architecture Diagram**

Below is a structured text-based architecture diagram illustrating the system flow from user interaction down to secure data storage and financial settlement:

```mermaid
graph TD
    %% Users & Entry Points
    subgraph Users ["Client Layer"]
        Patient["Patient / International Traveler"]
        Provider["Healthcare Provider / Hospital"]
    end

    %% Frontend Interface
    subgraph Frontend ["User Interface (React.js)"]
        UI["MediCard Web & Dashboard Portal"]
    end

    Patient -->|Login & Search Queries| UI
    Provider -->|Access Clinical Records / Billing| UI

    %% Application & AI Core
    subgraph Core ["AI & Application Services (Node.js / Python)"]
        Gateway["API Gateway & Router"]
        AISearch["AI Provider Search (Semantic Vector Engine & Pydantic)"]
        OCRModule["OCR Bill Extraction & Validation Engine"]
    end

    UI --> Gateway
    Gateway --> AISearch
    Gateway --> OCRModule

    %% Interoperability & Security Layers
    subgraph Interoperability ["Healthcare Interoperability & Identity"]
        FHIR["HL7 FHIR R4 & IPS Data Formatter"]
        Ontology["Clinical Vocabularies (SNOMED CT, LOINC, RxNorm)"]
        Consent["Consent & Digital ID Management"]
    end

    AISearch --> FHIR
    FHIR --> Ontology
    Gateway --> Consent

    %% Security & Blockchain
    subgraph Security ["Security & Audit Layer"]
        Encryption["AES-256-GCM Encryption"]
        Blockchain["Hyperledger Fabric (Consent Audit Logs)"]
    end

    Consent --> Encryption
    Consent --> Blockchain

    %% Financial Routing
    subgraph Finance ["Financial Routing & Clearinghouse"]
        FinRouting["Financial Coordination & VCC Issuing (Stripe/Nium/Marqeta)"]
        Adjudication["Clearinghouse Adjudication (X12 EDI 270/271/837P)"]
    end

    OCRModule --> FinRouting
    FinRouting --> Adjudication

    %% Persistent Storage
    subgraph Storage ["Database & Storage Layer"]
        DB[(MongoDB: User Profiles, Metadata, Logs)]
    end

    Encryption -.-> DB
    FHIR -.-> DB
    AISearch -.-> DB
