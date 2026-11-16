
# ResolveAI — Project Intent

## 1. Initial Problem

Customer support teams regularly deal with repetitive questions and customer issues involving orders, shipping, returns, refunds, defective products, and payment disputes.

Although many businesses have FAQs, policy documents, order management systems, and support procedures, this information is often spread across different sources.

Support agents must manually search through policies, check order information, understand the customer's issue, and determine the appropriate next action.

This creates several problems:

- Customers may wait too long for answers to relatively simple questions.
- Support agents spend time handling repetitive queries.
- Finding the correct policy or order information can require manual investigation.
- Generic AI chatbots may generate answers that are not supported by official company policies.
- When an AI system cannot answer a question, it may simply refuse or tell the customer to contact support without providing useful context.
- Repeated unanswered questions can reveal gaps in company documentation, but these gaps are not always systematically identified or addressed.

The problem is therefore not simply that businesses need another chatbot. They need a system that can investigate customer issues, use verified business information, provide reliable answers, and involve human support when necessary.

## 2. Target Users

### Primary Users: Customers

Customers who need assistance with:

- Order status and delivery tracking.
- Return and refund policies.
- Damaged or defective products.
- Warranty claims.
- Payment-related issues.
- Cancellations and other order-related questions.

### Secondary Users: Customer Support Agents

Support agents who need to:

- Investigate customer issues.
- Review conversation history.
- Access relevant order information.
- Understand why an AI system could not resolve a case.
- Review suggested resolutions.
- Respond to escalated tickets.
- Identify missing or unclear company policies.

### Additional Stakeholders: Support Administrators

Administrators responsible for:

- Maintaining company knowledge and policy documents.
- Reviewing recurring unanswered questions.
- Improving the support knowledge base.
- Monitoring ticket volumes and resolution activity.

## 3. Proposed Solution

Build ResolveAI, an AI-powered customer support resolution system.

ResolveAI will help customers receive answers to common questions while assisting support agents with investigating more complicated issues.

Rather than functioning as a basic question-answering chatbot, the system will combine:

1. **AI-powered issue understanding:** Identify customer intent and extract relevant information such as order IDs, products, reported problems, and requested resolutions.

2. **Knowledge-grounded responses:** Retrieve relevant information from company policies and documentation before generating an answer.

3. **Business data investigation:** Retrieve verified order and payment-status information through controlled backend tools.

4. **Evidence-based decision-making:** Use documented policies and deterministic backend business rules instead of allowing an LLM to independently make business decisions.

5. **Human escalation:** Create support tickets when a case requires human judgment, the customer requests an agent, or sufficient information is unavailable.

6. **Knowledge gap identification:** Track recurring questions that the existing knowledge base cannot answer so administrators can review and improve company documentation.

The system will have two main interfaces:

- A customer-facing support chat.
- An internal support and administration dashboard.

## 4. Expected Value

ResolveAI aims to provide value to both customers and support teams.

### For Customers

- Faster responses to common questions.
- Answers grounded in company policies.
- More useful assistance with order-related issues.
- A clear escalation path when human support is needed.
- Less need to repeat information during an investigation.

### For Support Teams

- Reduced repetitive manual investigation.
- Structured customer issue summaries.
- Relevant order and policy information in one place.
- Better context when handling escalated cases.
- Visibility into recurring knowledge gaps.
- An opportunity to improve the knowledge base using actual support questions.

## 5. Initial Scope

The initial project will focus on a fictional e-commerce business called ShopEase.

Using a fictional business allows us to create realistic policies, customers, orders, and support scenarios without relying on confidential business information or real customer data.

The initial version will include:

- A customer support chat interface.
- AI-based customer intent and information extraction.
- Retrieval-Augmented Generation (RAG) over fictional company policies.
- Order lookup through backend tools.
- Basic deterministic return and refund eligibility checks.
- Evidence-grounded AI responses.
- Handling of missing or unsupported information.
- Human escalation through an internal support ticket system.
- An administrative dashboard for reviewing and managing tickets.
- Knowledge gap tracking and knowledge base management.

The system will demonstrate three important scenarios:

1. Answering a customer question using relevant company policy documents.
2. Investigating a specific order using verified database information.
3. Handling an unsupported question by identifying missing knowledge, creating an escalation ticket, and allowing an administrator to provide an approved answer.

## 6. Initial Constraints

The project will be developed as a five-day AI-first development quest.

The following constraints will guide development:

- The complete MVP should use free-tier services and open-source technologies.
- No paid hosting, databases, or AI APIs should be required.
- All customer, order, and business information will be synthetic.
- AI-generated information must not be treated as verified business data.
- Unsupported policy questions must not result in invented answers.
- Important business decisions must be enforced by backend logic.
- Human review must be available for cases requiring judgment or approval.
- The implementation must remain understandable, testable, and maintainable.
- The project must be deployable and accessible through a public demonstration.

Free-tier quotas, storage limits, and hosting availability may restrict usage and uptime.

## 7. Out of Scope for the Initial Version

To keep the five-day MVP achievable, the following are excluded:

- Real e-commerce platform integrations.
- Real payment processing or automatic refunds.
- Integration with external helpdesk platforms.
- Real customer or confidential business data.
- Voice-based customer support.
- Multiple autonomous AI agents.
- Enterprise-grade role-based access control.
- Complex workflow automation.
- Large-scale production infrastructure.

These features may be considered in future versions if there is a clear need.

## 8. Success Criteria

The initial project will be considered successful if it demonstrates that:

- A customer can interact with ResolveAI through a support interface.
- The AI can understand customer issues and extract relevant information.
- Relevant company policies can be retrieved through RAG.
- Responses are grounded in retrieved evidence.
- The backend can retrieve actual order information through controlled tools.
- Unsupported questions are handled without hallucinating policies.
- Cases requiring human judgment create meaningful support tickets.
- Support agents can inspect the context behind escalated cases.
- Administrators can identify knowledge gaps and add approved information.
- Newly approved knowledge can be retrieved for subsequent questions.
- The complete application can be tested and deployed using free-tier services.

## 9. Project Vision

The broader vision for ResolveAI is to move beyond traditional FAQ-based chatbots toward AI-assisted customer support operations.

The goal is not to remove human support agents. It is to help customers resolve straightforward issues efficiently while giving human agents better information and context when their involvement is necessary.

ResolveAI should know when it has sufficient evidence to answer, when it needs additional information, and when it should hand the problem to a human.
