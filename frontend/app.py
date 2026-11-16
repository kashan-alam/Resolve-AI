"""Streamlit presentation layer for the ResolveAI demonstration."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

try:
    from .api_client import (
        ApiClientError,
        AuthenticationExpiredError,
        ResolveApiClient,
    )
except ImportError:
    from api_client import (
        ApiClientError,
        AuthenticationExpiredError,
        ResolveApiClient,
    )


CUSTOMER_IDENTITY_NOTICE = (
    "Demo identity selection only. This is not customer authentication."
)
TICKET_STATUSES = [
    "open",
    "pending_human_review",
    "assigned",
    "in_progress",
    "resolved",
    "closed",
]


def main() -> None:
    st.set_page_config(page_title="ResolveAI", page_icon="💬", layout="wide")
    st.title("ResolveAI")
    st.caption("ShopEase customer support demonstration")

    backend_url = os.getenv("BACKEND_API_URL", "").strip()
    if not backend_url:
        st.error("BACKEND_API_URL is not configured.")
        return

    mode = st.sidebar.radio("View", ["Customer Support", "Admin Dashboard"])
    client = ResolveApiClient(
        backend_url,
        token=st.session_state.get("admin_token"),
    )
    try:
        if mode == "Customer Support":
            render_customer_view(client)
        else:
            render_admin_view(client)
    finally:
        client.close()


def render_customer_view(client: ResolveApiClient) -> None:
    st.header("Customer Support")
    st.info(CUSTOMER_IDENTITY_NOTICE)

    try:
        customers = client.list_customers()
    except ApiClientError as error:
        st.error(str(error))
        return
    if not customers:
        st.warning("No demo customers are available.")
        return

    customer_by_id = {str(item["id"]): item for item in customers}
    customer_ids = list(customer_by_id)
    selected_customer_id = st.selectbox(
        "Select demo customer",
        customer_ids,
        key="selected_customer_id",
        format_func=lambda value: _customer_label(customer_by_id[value]),
    )
    if st.session_state.get("active_customer_id") != selected_customer_id:
        st.session_state.active_customer_id = selected_customer_id
        st.session_state.selected_conversation_id = None

    try:
        conversations = client.list_conversations(selected_customer_id)
    except ApiClientError as error:
        st.error(str(error))
        return

    conversation_ids = [str(item["id"]) for item in conversations]
    options = ["new"] + conversation_ids
    current_conversation = st.session_state.get("selected_conversation_id")
    default = current_conversation if current_conversation in conversation_ids else "new"
    selected_conversation = st.selectbox(
        "Conversation",
        options,
        index=options.index(default),
        key="conversation_selector",
        format_func=lambda value: (
            "Start a new conversation"
            if value == "new"
            else f"Conversation {value[:8]}"
        ),
    )
    if selected_conversation == "new":
        if st.button("Create conversation", key="create_conversation"):
            try:
                conversation = client.create_conversation(selected_customer_id)
            except ApiClientError as error:
                st.error(str(error))
            else:
                st.session_state.selected_conversation_id = str(conversation["id"])
                st.rerun()
        st.caption("Create a conversation to try policy, order, or escalation requests.")
        return

    st.session_state.selected_conversation_id = selected_conversation
    try:
        conversation = client.get_conversation(
            selected_customer_id, selected_conversation
        )
    except ApiClientError as error:
        st.error(str(error))
        return
    _render_messages(conversation.get("messages", []))
    _render_customer_message_form(client, selected_customer_id, selected_conversation)


def _render_customer_message_form(
    client: ResolveApiClient,
    customer_id: str,
    conversation_id: str,
) -> None:
    st.subheader("Send a message")
    with st.form("customer_message_form", clear_on_submit=True):
        content = st.text_area(
            "Message",
            max_chars=10_000,
            placeholder="Ask about a policy, order, or request human support.",
        )
        submitted = st.form_submit_button(
            "Send",
            disabled=st.session_state.get("message_submission_in_progress", False),
        )
    if not submitted:
        return
    if not content.strip():
        st.warning("Enter a message before sending.")
        return

    st.session_state.message_submission_in_progress = True
    try:
        result = client.send_message(customer_id, conversation_id, content.strip())
    except ApiClientError as error:
        st.error(str(error))
    else:
        _render_workflow_result(result)
        st.rerun()
    finally:
        st.session_state.message_submission_in_progress = False


def _render_workflow_result(result: dict[str, Any]) -> None:
    if result.get("insufficient_evidence"):
        st.warning("The available policy evidence was insufficient for a grounded answer.")
    for citation in result.get("policy_citations", []):
        with st.expander(f"Source: {citation.get('document_title', 'Policy document')}"):
            st.write(citation.get("chunk_text", ""))
    if result.get("order_result"):
        st.success("Verified order information")
        st.json(result["order_result"])
    ticket = result.get("ticket")
    if ticket:
        st.info(
            f"Human review requested ({ticket.get('ticket_number', 'ticket')}, "
            f"status: {ticket.get('status', 'unknown')})."
        )


def render_admin_view(client: ResolveApiClient) -> None:
    st.header("Admin Ticket Dashboard")
    if not st.session_state.get("admin_token"):
        _render_admin_login(client)
        return

    if st.sidebar.button("Log out", key="admin_logout"):
        _clear_admin_session()
        st.rerun()

    status_filter = st.selectbox("Filter by status", ["all"] + TICKET_STATUSES)
    try:
        tickets = client.list_tickets(None if status_filter == "all" else status_filter)
    except AuthenticationExpiredError as error:
        _clear_admin_session()
        st.warning(str(error))
        st.rerun()
    except ApiClientError as error:
        st.error(str(error))
        return

    if not tickets:
        st.info("No tickets match this filter.")
        return

    ticket_by_id = {str(item["id"]): item for item in tickets}
    selected_ticket_id = st.selectbox(
        "Ticket",
        list(ticket_by_id),
        format_func=lambda value: _ticket_label(ticket_by_id[value]),
    )
    try:
        ticket = client.get_ticket(selected_ticket_id)
    except AuthenticationExpiredError as error:
        _clear_admin_session()
        st.warning(str(error))
        st.rerun()
    except ApiClientError as error:
        st.error(str(error))
        return
    _render_ticket_detail(ticket)
    _render_ticket_update_form(client, ticket)


def _render_admin_login(client: ResolveApiClient) -> None:
    st.subheader("Admin login")
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if not submitted:
        return
    try:
        token_response = client.login(username, password)
    except ApiClientError as error:
        st.error(str(error))
        return
    st.session_state.admin_token = token_response["access_token"]
    st.session_state.admin_username = username
    st.rerun()


def _render_ticket_update_form(
    client: ResolveApiClient, ticket: dict[str, Any]
) -> None:
    st.subheader("Update ticket")
    with st.form(f"ticket_update_{ticket['id']}"):
        status = st.selectbox(
            "Status",
            TICKET_STATUSES,
            index=TICKET_STATUSES.index(ticket["status"])
            if ticket["status"] in TICKET_STATUSES
            else 0,
        )
        internal_note = st.text_area("Internal note")
        resolution = st.text_area("Resolution")
        submitted = st.form_submit_button("Save update")
    if not submitted:
        return
    try:
        updated = client.update_ticket(
            str(ticket["id"]),
            status=status if status != ticket["status"] else None,
            internal_note=internal_note.strip() or None,
            resolution=resolution.strip() or None,
        )
    except AuthenticationExpiredError as error:
        _clear_admin_session()
        st.warning(str(error))
        st.rerun()
    except ApiClientError as error:
        st.error(str(error))
        return
    st.success(f"Ticket {updated['ticket_number']} updated.")
    st.rerun()


def _render_messages(messages: list[dict[str, Any]]) -> None:
    for message in messages:
        role = "user" if message.get("sender_type") == "customer" else "assistant"
        with st.chat_message(role):
            st.write(message.get("content", ""))


def _render_ticket_detail(ticket: dict[str, Any]) -> None:
    st.subheader(
        f"{ticket.get('ticket_number', 'Ticket')} - {ticket.get('status', 'unknown')}"
    )
    st.write(ticket.get("escalation_reason") or "No escalation reason recorded.")
    if ticket.get("final_response"):
        st.markdown("**Resolution**")
        st.write(ticket["final_response"])
    with st.expander("Conversation"):
        _render_messages(ticket.get("messages", []))
    with st.expander("Policy evidence"):
        for evidence in ticket.get("evidence", []):
            st.markdown(f"**{evidence.get('document_title', 'Evidence')}**")
            st.write(evidence.get("chunk_text", ""))
    with st.expander("Ticket events"):
        for event in ticket.get("events", []):
            st.write(
                f"{event.get('event_type', 'event')}: "
                f"{event.get('internal_note') or event.get('new_value') or ''}"
            )


def _clear_admin_session() -> None:
    st.session_state.pop("admin_token", None)
    st.session_state.pop("admin_username", None)


def _customer_label(customer: dict[str, Any]) -> str:
    return f"{customer.get('name', 'Customer')} ({customer.get('email', '')})"


def _ticket_label(ticket: dict[str, Any]) -> str:
    return f"{ticket.get('ticket_number', 'Ticket')} - {ticket.get('status', 'unknown')}"


if __name__ == "__main__":
    main()
