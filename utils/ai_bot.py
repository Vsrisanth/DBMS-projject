"""
Civic Connects - Intelligent Civic Assistant Engine
Processes citizen inquiries regarding complaints, portal navigation,
department jurisdictions, and real-time ticket tracking.
"""

import re
from db import execute_query

CIVIC_FAQS = {
    "report": (
        "**To report a new civic issue:**\n"
        "1. Click **Report Issue** from the sidebar.\n"
        "2. Select the municipal category (e.g., Road Damage, Water Supply, Electricity).\n"
        "3. Provide a clear location or click **Detect My Location** for automatic GPS tagging.\n"
        "4. Describe the problem in detail and optionally attach an evidence photo (max 5MB).\n"
        "5. Submit the form to immediately receive a unique tracking Ticket ID (e.g. `#CC-XXXX`)."
    ),
    "track": (
        "**To track your existing complaint:**\n"
        "• Click **Track Complaint** in the sidebar and enter your ticket number (e.g. `#CC-8421`).\n"
        "• Alternatively, visit **My Complaints** to view all your grievances, milestone progress, and official municipal engineer remarks."
    ),
    "milestones": (
        "**Complaint Status Milestones:**\n"
        "1. **Submitted**: Grievance received and entered into the municipal dispatch registry.\n"
        "2. **Under Review**: Civic engineers are inspecting the report and assessing department routing.\n"
        "3. **In Progress**: Work order generated; municipal field crew dispatched on-site.\n"
        "4. **Resolved**: Maintenance verified complete by the department with official remarks."
    ),
    "categories": (
        "**Supported Municipal Categories & Departments:**\n"
        "• **Road Damage**: Potholes, asphalt cracks, curb damage (Roads & Highways)\n"
        "• **Water Supply**: Pipeline leaks, water contamination, low pressure (Water Supply & Sewerage)\n"
        "• **Electricity**: Sparking lines, transformer faults, blackout (Power Board)\n"
        "• **Garbage Management**: Overflowing dumpsters, illegal dumps (Sanitation)\n"
        "• **Streetlight Failure**: Dark stretches, non-functional poles (Lighting & Signals)\n"
        "• **Drainage**: Clogged stormwater lines, open manholes (Flood Control)\n"
        "• **Public Works & Parks**: Hazardous tree branches, park maintenance"
    ),
    "emergency": (
        "**Emergency Municipal Contacts (India):**\n"
        "🚨 **National Emergency**: Call **112** immediately.\n"
        "⚡ **Electricity Board Emergency**: Call **1912**.\n"
        "💧 **Water Supply / Sewage Helpline**: Call **1916**.\n"
        "🏢 **Civic Grievance Helpline**: Call **1800-123-2026**."
    ),
    "time": (
        "**Estimated Resolution Timeframes:**\n"
        "• **High Priority / Hazard** (live wires, main bursts): 4 to 24 hours.\n"
        "• **Medium Priority** (potholes, streetlights): 2 to 5 business days.\n"
        "• **Standard Works** (drain desilting, road resurfacing): 5 to 10 business days."
    ),
    "anonymity": (
        "**Anonymous Feedback:**\n"
        "If you want to report a portal bug or share feedback anonymously, visit **Feedback & Report** in the sidebar. "
        "Our system explicitly strips your user ID, name, email, and IP address from the submission payload before saving."
    )
}

def process_ai_message(user_msg):
    """
    Analyzes citizen message and returns a helpful, structured response.
    Includes automated live ticket tracking if ticket ID is referenced.
    """
    if not user_msg:
        return {
            "reply": "Hello! I am your Civic AI Assistant. How can I help you today? You can ask about filing grievances, tracking tickets, or municipal services.",
            "suggestions": ["How do I report a pothole?", "Track ticket #CC-8421", "Municipal categories", "Emergency contacts"]
        }

    raw = user_msg.strip()
    msg_lower = raw.lower()

    # 1. Check for Ticket Number Pattern (#CC-XXXX or CC-XXXX or just digits like 8421)
    ticket_match = re.search(r'#?CC-?(\d{3,5})', raw, re.IGNORECASE)
    if ticket_match:
        digits = ticket_match.group(1)
        formatted_ticket = f"#CC-{digits}"
        try:
            complaint = execute_query(
                """SELECT c.*, d.name AS dept_name 
                   FROM complaints c 
                   LEFT JOIN departments d ON c.department_id = d.id 
                   WHERE c.ticket_number = %s""",
                (formatted_ticket,),
                one=True
            )
            if complaint:
                status_display = complaint['status'].replace('_', ' ').title()
                dept_display = complaint.get('dept_name') or 'Under Routing Assessment'
                remarks = complaint.get('admin_remarks') or 'No official remarks posted yet.'
                clean_ticket = complaint['ticket_number'].replace('#', '')
                
                reply = (
                    f"🔎 **Ticket Found: `{complaint['ticket_number']}`**\n\n"
                    f"• **Title**: {complaint['title']}\n"
                    f"• **Category**: {complaint['category']}\n"
                    f"• **Current Status**: **{status_display}**\n"
                    f"• **Assigned Department**: {dept_display}\n"
                    f"• **Location**: {complaint['location']}\n"
                    f"• **Official Remarks**: *\"{remarks}\"*\n\n"
                    f"👉 **[Click here to view interactive timeline](/citizen/track?ticket={clean_ticket})**"
                )
                return {
                    "reply": reply,
                    "suggestions": ["What do milestones mean?", "How long does resolution take?", "Emergency contacts"]
                }
            else:
                return {
                    "reply": f"⚠️ I searched the municipal database, but ticket **`{formatted_ticket}`** was not found. Please double-check your ticket ID format (e.g. `#CC-8421`) or verify under **My Complaints**.",
                    "suggestions": ["How to track complaint", "Report a new issue", "Contact City Hall"]
                }
        except Exception as e:
            return {
                "reply": f"Unable to fetch ticket details at this moment: {str(e)}",
                "suggestions": ["Track ticket", "Filing FAQs"]
            }

    # 2. Check for Intent / FAQs
    if any(k in msg_lower for k in ["pothole", "report", "file", "submit", "lodge", "how to"]):
        return {
            "reply": CIVIC_FAQS["report"],
            "suggestions": ["Municipal categories", "How long does it take?", "Emergency contacts"]
        }

    if any(k in msg_lower for k in ["track", "status", "progress", "ticket", "where is my"]):
        return {
            "reply": CIVIC_FAQS["track"],
            "suggestions": ["Track ticket #CC-8421", "What do milestones mean?", "Report an issue"]
        }

    if any(k in msg_lower for k in ["milestone", "step", "pending", "in progress", "resolved"]):
        return {
            "reply": CIVIC_FAQS["milestones"],
            "suggestions": ["How long does resolution take?", "Track ticket", "Report an issue"]
        }

    if any(k in msg_lower for k in ["category", "categories", "department", "jurisdiction", "water", "electricity", "road", "garbage"]):
        return {
            "reply": CIVIC_FAQS["categories"],
            "suggestions": ["How to report an issue", "Emergency contacts", "Track ticket"]
        }

    if any(k in msg_lower for k in ["emergency", "urgent", "danger", "fire", "spark", "flood", "helpline", "phone", "contact"]):
        return {
            "reply": CIVIC_FAQS["emergency"],
            "suggestions": ["Report an issue", "Contact City Hall", "Municipal categories"]
        }

    if any(k in msg_lower for k in ["time", "duration", "how long", "turnaround", "sla", "days"]):
        return {
            "reply": CIVIC_FAQS["time"],
            "suggestions": ["What do milestones mean?", "Report an issue", "Emergency contacts"]
        }

    if any(k in msg_lower for k in ["anonymous", "privacy", "bug", "feedback"]):
        return {
            "reply": CIVIC_FAQS["anonymity"],
            "suggestions": ["Report an issue", "Track ticket", "Contact support"]
        }

    # 3. Friendly conversational greetings
    if any(k in msg_lower for k in ["hello", "hi", "hey", "good morning", "good evening"]):
        return {
            "reply": "👋 Hello! I am your 24/7 Civic Connects Assistant. How can I assist you with municipal services today?",
            "suggestions": ["How do I report a pothole?", "Track a complaint", "Supported categories", "Emergency contacts"]
        }

    if any(k in msg_lower for k in ["thank", "thanks", "appreciate"]):
        return {
            "reply": "You're very welcome! Civic Connects is dedicated to keeping our neighborhoods safe and clean. Let me know if you need anything else!",
            "suggestions": ["Report an issue", "Track another ticket", "Back to dashboard"]
        }

    # 4. Default Fallback
    return {
        "reply": (
            "I'm here to help with all Civic Connects services! You can ask me how to report an issue, "
            "track an existing complaint by its ticket number (e.g., `#CC-8421`), or learn about municipal categories."
        ),
        "suggestions": [
            "How do I report a pothole?",
            "Track ticket #CC-8421",
            "Supported categories",
            "Emergency contacts"
        ]
    }
