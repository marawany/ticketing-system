#!/usr/bin/env python3
"""
Generate Synthetic Ticket Dataset

Creates 1000 synthetic support tickets with a 3-level classification hierarchy.
The hierarchy is designed to represent realistic customer support scenarios.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from uuid import uuid4

# =============================================================================
# CLASSIFICATION HIERARCHY
# =============================================================================
# This defines the 3-level classification structure that will be used
# to populate Neo4j and classify tickets

CLASSIFICATION_HIERARCHY: Dict[str, Dict[str, List[str]]] = {
    # Level 1: Technical Support
    "Technical Support": {
        "Authentication": [
            "Password Reset Issues",
            "Two-Factor Authentication",
            "SSO Integration Problems",
            "Account Lockout",
            "Login Failures",
        ],
        "Performance": [
            "Slow Response Time",
            "Timeout Errors",
            "High Latency",
            "Resource Exhaustion",
            "Memory Issues",
        ],
        "Integration": [
            "API Errors",
            "Webhook Failures",
            "Data Sync Issues",
            "Third-Party Connectivity",
            "SDK Problems",
        ],
        "Infrastructure": [
            "Server Downtime",
            "Database Connectivity",
            "Network Issues",
            "SSL Certificate Problems",
            "DNS Resolution",
        ],
        "Data Issues": [
            "Data Corruption",
            "Missing Records",
            "Duplicate Entries",
            "Import Failures",
            "Export Problems",
        ],
    },
    # Level 1: Billing & Payments
    "Billing & Payments": {
        "Invoicing": [
            "Missing Invoice",
            "Incorrect Amount",
            "Duplicate Charges",
            "Invoice Format Issues",
            "Tax Calculation Errors",
        ],
        "Payment Processing": [
            "Failed Transactions",
            "Refund Requests",
            "Chargeback Disputes",
            "Payment Method Issues",
            "Currency Conversion",
        ],
        "Subscription": [
            "Plan Changes",
            "Cancellation Requests",
            "Renewal Problems",
            "Trial Extension",
            "Downgrade Issues",
        ],
        "Credits & Discounts": [
            "Promo Code Issues",
            "Credit Application",
            "Discount Not Applied",
            "Loyalty Points",
            "Referral Rewards",
        ],
    },
    # Level 1: Account Management
    "Account Management": {
        "Profile Settings": [
            "Update Contact Info",
            "Change Email Address",
            "Profile Picture Issues",
            "Timezone Settings",
            "Language Preferences",
        ],
        "Access Control": [
            "Permission Changes",
            "Role Assignment",
            "Team Management",
            "User Invitation Issues",
            "Deactivation Requests",
        ],
        "Security": [
            "Suspicious Activity",
            "Security Audit Request",
            "Compliance Questions",
            "Data Privacy",
            "GDPR Requests",
        ],
        "Migration": [
            "Account Transfer",
            "Data Export Request",
            "Account Merge",
            "Legacy System Migration",
            "Platform Switch",
        ],
    },
    # Level 1: Product Features
    "Product Features": {
        "Feature Requests": [
            "New Functionality",
            "Enhancement Suggestions",
            "UI Improvements",
            "Workflow Automation",
            "Reporting Capabilities",
        ],
        "Bug Reports": [
            "UI Glitches",
            "Functional Bugs",
            "Mobile App Issues",
            "Browser Compatibility",
            "Calculation Errors",
        ],
        "Documentation": [
            "Missing Documentation",
            "Unclear Instructions",
            "API Reference Questions",
            "Tutorial Requests",
            "Changelog Queries",
        ],
        "Training": [
            "Onboarding Assistance",
            "Advanced Training",
            "Best Practices",
            "Use Case Guidance",
            "Certification Questions",
        ],
    },
    # Level 1: Sales & Licensing
    "Sales & Licensing": {
        "Pricing": [
            "Quote Requests",
            "Volume Discounts",
            "Custom Pricing",
            "Competitive Comparison",
            "ROI Analysis",
        ],
        "Licensing": [
            "License Activation",
            "License Transfer",
            "Compliance Verification",
            "Usage Limits",
            "Enterprise Agreement",
        ],
        "Contracts": [
            "Contract Renewal",
            "Terms Negotiation",
            "SLA Questions",
            "Partnership Inquiries",
            "Reseller Agreements",
        ],
    },
}

# =============================================================================
# TICKET TEMPLATES
# =============================================================================
# Templates for generating realistic ticket content

TICKET_TEMPLATES: Dict[str, List[Dict[str, str]]] = {
    "Password Reset Issues": [
        {
            "title": "Cannot reset password - link expired",
            "description": "I requested a password reset but by the time I clicked the link it had already expired. The email took over an hour to arrive. Please send a new reset link or extend the expiration time."
        },
        {
            "title": "Password reset email not received",
            "description": "I've requested password reset multiple times but haven't received any email. Already checked spam folder. My email is {email}. Please help me regain access to my account."
        },
        {
            "title": "New password not accepted after reset",
            "description": "Successfully reset my password using the link, but when I try to login with the new password it says invalid credentials. I've tried multiple browsers."
        },
    ],
    "Two-Factor Authentication": [
        {
            "title": "Lost access to authenticator app",
            "description": "I changed phones and forgot to transfer my authenticator app. Now I can't get the 2FA codes to login. I have my backup codes somewhere but can't find them. Need help disabling 2FA temporarily."
        },
        {
            "title": "2FA codes not working",
            "description": "The codes from my authenticator app keep saying invalid. I've synced the time on my phone. This started happening yesterday after the app update."
        },
    ],
    "SSO Integration Problems": [
        {
            "title": "SAML SSO returning error",
            "description": "Our company SSO integration stopped working this morning. Getting 'SAML Response validation failed' error. Nothing changed on our end. Error code: SAML_INVALID_RESPONSE_001."
        },
        {
            "title": "Cannot configure Azure AD SSO",
            "description": "Following the documentation to set up Azure AD SSO but getting stuck at the callback URL configuration. The test connection keeps failing with a 403 error."
        },
    ],
    "Account Lockout": [
        {
            "title": "Account locked after failed login attempts",
            "description": "My account got locked after entering wrong password. It's been over 30 minutes but still can't login. The system says account is locked for security reasons."
        },
        {
            "title": "Locked out - suspicious activity detected",
            "description": "Received email about suspicious activity and now my account is locked. I was just traveling and logging in from a different country. Please unlock my account."
        },
    ],
    "Login Failures": [
        {
            "title": "Cannot login - blank page after credentials",
            "description": "When I enter my credentials and click login, the page just goes blank. No error message, just a white screen. Happens on Chrome and Firefox. Cleared cache already."
        },
        {
            "title": "Login button not responding",
            "description": "The login button on the website doesn't do anything when clicked. Console shows JavaScript errors. Using latest Chrome on Windows 11."
        },
    ],
    "Slow Response Time": [
        {
            "title": "Dashboard taking 30+ seconds to load",
            "description": "The main dashboard has been extremely slow this week. Takes over 30 seconds to load, sometimes times out completely. Other pages load fine. We have 50 team members experiencing this."
        },
        {
            "title": "Reports page is unusably slow",
            "description": "Generating any report takes 5+ minutes now. Last month it was instant. Nothing changed in our data volume. This is affecting our daily operations."
        },
    ],
    "Timeout Errors": [
        {
            "title": "Constant 504 Gateway Timeout errors",
            "description": "Getting frequent 504 errors throughout the day, especially when saving large forms. Started happening after your last maintenance window. Very frustrating."
        },
        {
            "title": "API calls timing out",
            "description": "Our integration is failing because API calls are timing out after 30 seconds. These calls used to complete in 2-3 seconds. Endpoint: /api/v2/data/sync"
        },
    ],
    "High Latency": [
        {
            "title": "Extreme latency from EU region",
            "description": "Our European users are experiencing 5-10 second latency on all operations. US users are fine. Is there an issue with your EU servers? Started 3 days ago."
        },
    ],
    "API Errors": [
        {
            "title": "API returning 500 errors intermittently",
            "description": "Our production integration is getting random 500 errors from your API. Happens about 10% of the time. Same request works if retried. Started 2 days ago. Request ID: req_abc123xyz"
        },
        {
            "title": "API rate limit being hit unexpectedly",
            "description": "We're getting 429 errors even though we're well under our rate limit. Dashboard shows 1000/10000 calls used but API returns rate_limit_exceeded. Plan: Enterprise."
        },
    ],
    "Webhook Failures": [
        {
            "title": "Webhooks not being delivered",
            "description": "Our webhook endpoint stopped receiving events 6 hours ago. The endpoint is up and accessible. Last event received at 3:45 PM UTC. URL: https://api.oursite.com/webhooks/nexusflow"
        },
        {
            "title": "Webhook payload format changed",
            "description": "Our webhook processing is failing because the payload format seems to have changed. Field 'user_id' is now 'userId'. This broke our automation. Was there an API update?"
        },
    ],
    "Data Sync Issues": [
        {
            "title": "Salesforce sync not updating contacts",
            "description": "The Salesforce integration was working fine until yesterday. New contacts aren't syncing over. The connection shows as active. Last successful sync was 24 hours ago."
        },
        {
            "title": "Data sync running but no changes reflected",
            "description": "Sync jobs show as completed successfully but changes made in the source system aren't appearing. Tried manual sync too. Integration: HubSpot CRM."
        },
    ],
    "Third-Party Connectivity": [
        {
            "title": "Stripe integration disconnected",
            "description": "Our Stripe integration keeps disconnecting. Have to re-authorize every few hours. This is causing payment failures. Never had this issue before last week's update."
        },
    ],
    "SDK Problems": [
        {
            "title": "Python SDK throwing SSL errors",
            "description": "After upgrading to v2.5.0 of your Python SDK, getting SSL certificate verification errors. Worked fine on v2.4.x. Using Python 3.11 on Ubuntu 22.04."
        },
        {
            "title": "JavaScript SDK memory leak",
            "description": "The JS SDK seems to have a memory leak. Browser memory usage grows continuously when using real-time subscriptions. Have to refresh page every hour. SDK version 3.2.1."
        },
    ],
    "Server Downtime": [
        {
            "title": "Service completely unavailable",
            "description": "Your entire service has been down for the past 45 minutes. Status page shows all green but we cannot access anything. This is a production emergency for us!"
        },
    ],
    "Database Connectivity": [
        {
            "title": "Database connection pool exhausted",
            "description": "Getting 'connection pool exhausted' errors when trying to run queries. This started after we increased our team size. Current plan should support 100 users."
        },
    ],
    "Failed Transactions": [
        {
            "title": "Payment declined but money taken",
            "description": "I tried to pay my subscription but got a 'payment declined' message. However, my bank shows the money was deducted. Transaction ID: TXN_789456123. Please investigate."
        },
        {
            "title": "Recurring payment failing every month",
            "description": "My subscription payment has failed for the 3rd month in a row. Card is valid and has funds. Other subscriptions charge fine. Getting error: CARD_DECLINED_GENERIC."
        },
    ],
    "Refund Requests": [
        {
            "title": "Request refund for double charge",
            "description": "I was charged twice for my monthly subscription on Dec 15th. Amounts: $99.00 each. Please refund the duplicate charge. Invoice numbers: INV-2024-1234 and INV-2024-1235."
        },
        {
            "title": "Refund for unused annual subscription",
            "description": "I purchased an annual plan but need to cancel due to company closure. Only used 2 months. Requesting prorated refund for the remaining 10 months per your refund policy."
        },
    ],
    "Missing Invoice": [
        {
            "title": "Invoice for October not received",
            "description": "I haven't received my invoice for October 2024. Our accounting department needs it for month-end close. Account ID: ACC-55789. Please resend to billing@company.com"
        },
    ],
    "Incorrect Amount": [
        {
            "title": "Overcharged on last invoice",
            "description": "Last invoice shows $599 but our plan is $299/month. We didn't add any users or features. Please explain the extra charges or correct the invoice."
        },
    ],
    "Plan Changes": [
        {
            "title": "Need to upgrade to Business plan",
            "description": "We need to upgrade from Starter to Business plan. Want to keep our current billing date. How do we proceed? Do we get prorated credit for current month?"
        },
        {
            "title": "Downgrade not taking effect",
            "description": "I downgraded from Pro to Basic plan 2 weeks ago but I'm still being charged Pro rates. Confirmation email shows downgrade was processed. Please fix billing."
        },
    ],
    "Cancellation Requests": [
        {
            "title": "Need to cancel subscription immediately",
            "description": "Due to budget cuts, we need to cancel our subscription effective immediately. Please confirm cancellation and any final charges. We'll need data export first."
        },
    ],
    "Update Contact Info": [
        {
            "title": "Change billing email address",
            "description": "Need to update billing email from old@company.com to new@company.com. The settings page won't let me change it, says to contact support."
        },
    ],
    "Permission Changes": [
        {
            "title": "User can't access admin settings",
            "description": "I promoted John Smith (john@company.com) to admin but he still can't see admin settings. I've logged out and back in on his account. Permissions show as admin."
        },
        {
            "title": "Remove user access urgently",
            "description": "URGENT: Need to immediately revoke access for terminated employee. Email: jane.doe@company.com. They should not have access to any company data as of today."
        },
    ],
    "Suspicious Activity": [
        {
            "title": "Unknown logins from Russia",
            "description": "I see login attempts from Russia in my activity log but I've never been there. Some show as successful. Please secure my account and tell me if data was accessed."
        },
    ],
    "Data Export Request": [
        {
            "title": "Need complete data export",
            "description": "Requesting a complete export of all our data for backup purposes. Need all tickets, users, and configurations. Preferred format: JSON or CSV."
        },
    ],
    "New Functionality": [
        {
            "title": "Feature request: Dark mode",
            "description": "Would love to have a dark mode option. Working late hours and the bright interface is straining. Many users in our org have requested this."
        },
        {
            "title": "Request: Bulk import from CSV",
            "description": "We need ability to bulk import records via CSV. Currently have to enter 500+ items manually. This would save us days of work."
        },
    ],
    "UI Glitches": [
        {
            "title": "Dropdown menu not closing",
            "description": "The dropdown menus in the navigation bar don't close when clicking elsewhere. Have to click the menu item again. Very annoying. Chrome 120 on Mac."
        },
        {
            "title": "Modal dialogs appearing behind overlay",
            "description": "Pop-up dialogs are appearing behind the dark overlay so I can't see them. Have to tab blindly to close them. Started after latest update."
        },
    ],
    "Functional Bugs": [
        {
            "title": "Search not returning correct results",
            "description": "Search function is broken. Searching for exact ticket number returns 'no results' but the ticket exists. Can find it manually. Search: TKT-45678"
        },
        {
            "title": "Filters reset when changing pages",
            "description": "When I apply filters and go to page 2 of results, all filters reset and shows everything. Have to re-apply filters on each page. Very frustrating."
        },
    ],
    "Mobile App Issues": [
        {
            "title": "App crashes when opening notifications",
            "description": "iOS app crashes immediately when tapping the notifications icon. Started after updating to version 4.2.0. iPhone 14 Pro, iOS 17.2."
        },
    ],
    "Missing Documentation": [
        {
            "title": "No docs for new API endpoint",
            "description": "Found a new endpoint /api/v2/analytics/advanced in the changelog but there's no documentation for it. Need to know the parameters and response format."
        },
    ],
    "Quote Requests": [
        {
            "title": "Need enterprise pricing for 500 users",
            "description": "We're evaluating your platform for company-wide deployment. Need a quote for 500 users with SSO, audit logs, and dedicated support. Timeline: Q2 decision."
        },
    ],
    "License Activation": [
        {
            "title": "Cannot activate enterprise license",
            "description": "Received our enterprise license key yesterday but it says 'invalid key' when trying to activate. Key: NXFL-ENT-2024-XXXXX (full key in secure channel)."
        },
    ],
    "Contract Renewal": [
        {
            "title": "Questions about renewal terms",
            "description": "Our contract is up for renewal in 60 days. Would like to discuss updated terms, especially around the new AI features pricing. Current contract: CTR-2023-789."
        },
    ],
    # Add more templates for remaining categories...
    "Resource Exhaustion": [
        {
            "title": "Hitting storage limits frequently",
            "description": "We keep hitting our storage quota every few weeks. Need to understand what's consuming space and options to increase limits without upgrading entire plan."
        },
    ],
    "Memory Issues": [
        {
            "title": "Out of memory errors in reports",
            "description": "Getting 'out of memory' errors when generating large reports. Specifically the monthly analytics report with 100k+ records. Worked last month."
        },
    ],
    "Data Corruption": [
        {
            "title": "Customer records showing garbled text",
            "description": "Some customer records are showing garbled/corrupted text instead of names. Noticed in records imported last week. About 200 affected records."
        },
    ],
    "Missing Records": [
        {
            "title": "Transactions from yesterday disappeared",
            "description": "All transactions from yesterday (Dec 15) are missing from our account. They were there this morning. We had about 150 transactions. This is critical!"
        },
    ],
    "Duplicate Entries": [
        {
            "title": "System creating duplicate contacts",
            "description": "The system is creating duplicate contacts every time we import. Same email addresses appearing 3-4 times. Need help deduplicating and preventing this."
        },
    ],
    "Import Failures": [
        {
            "title": "CSV import failing silently",
            "description": "Tried to import a 5000 row CSV file. Shows 'import complete' but only 1000 records imported. No error messages. File validates fine per your format guide."
        },
    ],
    "Export Problems": [
        {
            "title": "Export downloads empty file",
            "description": "When I try to export my data to CSV, it downloads a file with only headers, no data rows. Tried multiple browsers and formats. Account definitely has data."
        },
    ],
    "Network Issues": [
        {
            "title": "Intermittent connection drops",
            "description": "Connection to your service drops randomly throughout the day. Usually reconnects in a few seconds but we lose unsaved work. Our internet is stable."
        },
    ],
    "SSL Certificate Problems": [
        {
            "title": "SSL certificate warning on custom domain",
            "description": "Getting 'certificate not trusted' warning on our custom domain portal.company.com. Was working until yesterday. Certificate shows as expired."
        },
    ],
    "DNS Resolution": [
        {
            "title": "Cannot resolve api.nexusflow.io",
            "description": "Our servers can't resolve api.nexusflow.io intermittently. DNS lookups fail about 20% of the time. Using Google DNS 8.8.8.8. Other domains resolve fine."
        },
    ],
    "Duplicate Charges": [
        {
            "title": "Charged 3 times for same month",
            "description": "I've been charged 3 times for November subscription. $49.99 x3 = $149.97 total. Only should be one charge. Please refund the extra two charges immediately."
        },
    ],
    "Invoice Format Issues": [
        {
            "title": "Invoice missing company tax ID",
            "description": "Our accounting requires tax ID on invoices for compliance. Your invoices don't include this field. Can you add our tax ID: XX-1234567 to future invoices?"
        },
    ],
    "Tax Calculation Errors": [
        {
            "title": "Wrong tax rate applied",
            "description": "I'm being charged 10% tax but my state has 6% sales tax. This has been happening for several months. Please correct and credit the difference."
        },
    ],
    "Chargeback Disputes": [
        {
            "title": "Received chargeback notification",
            "description": "Got email about a chargeback on my account but I never disputed any charge. Someone may have stolen my card info. Please help resolve this."
        },
    ],
    "Payment Method Issues": [
        {
            "title": "Cannot add new credit card",
            "description": "Trying to update my payment method but the form won't accept my new card. Just says 'card declined' but the card works everywhere else. Card: Visa ending 4242."
        },
    ],
    "Currency Conversion": [
        {
            "title": "Exchange rate seems wrong",
            "description": "I'm in EU and paying in EUR. The amount converted from USD seems 15% higher than current exchange rates. Are you using a different rate?"
        },
    ],
    "Renewal Problems": [
        {
            "title": "Auto-renewal failed",
            "description": "My subscription was supposed to auto-renew but got cancellation notice instead. Payment method is valid with sufficient funds. Please reinstate my account."
        },
    ],
    "Trial Extension": [
        {
            "title": "Need trial extension to complete evaluation",
            "description": "Our evaluation is taking longer due to holidays. Trial ends in 2 days but we need 2 more weeks to complete testing. Can you extend our trial?"
        },
    ],
    "Downgrade Issues": [
        {
            "title": "Lost data after plan downgrade",
            "description": "After downgrading from Pro to Starter, we lost access to historical data beyond 30 days. Wasn't warned this would happen. Can we recover that data?"
        },
    ],
    "Promo Code Issues": [
        {
            "title": "Promo code SAVE20 not working",
            "description": "Trying to apply promo code SAVE20 from your email campaign but it says 'invalid code'. The email says it's valid until Dec 31. Order value: $299."
        },
    ],
    "Credit Application": [
        {
            "title": "Credit not applied to invoice",
            "description": "I have a $50 credit on my account from a previous issue but it wasn't applied to my last invoice. Credit ref: CR-2024-456. Please apply to next invoice."
        },
    ],
    "Discount Not Applied": [
        {
            "title": "Annual discount not reflected",
            "description": "I signed up for annual billing expecting 20% discount but I'm being charged full price. Confirmation email mentions annual discount. Please correct."
        },
    ],
    "Loyalty Points": [
        {
            "title": "Where did my reward points go?",
            "description": "I had 5,000 loyalty points last month but now showing 0. Didn't redeem anything. Please restore my points and explain what happened."
        },
    ],
    "Referral Rewards": [
        {
            "title": "Referral bonus not received",
            "description": "I referred 3 people who signed up and paid. The referral page shows them as confirmed but I haven't received my $50 credits. Referral code: REF-MYCODE."
        },
    ],
    "Profile Picture Issues": [
        {
            "title": "Cannot upload profile picture",
            "description": "Getting error 'file too large' when uploading a 500KB JPEG. Your docs say limit is 5MB. Tried PNG too, same error. Need to update my profile picture."
        },
    ],
    "Timezone Settings": [
        {
            "title": "Events showing wrong time",
            "description": "All scheduled events show 8 hours ahead of actual time. My timezone is set to PST correctly. This is causing missed meetings and deadlines."
        },
    ],
    "Language Preferences": [
        {
            "title": "Interface showing wrong language",
            "description": "Despite setting English as my language, parts of the interface keep showing in Spanish. Especially error messages and email notifications."
        },
    ],
    "Role Assignment": [
        {
            "title": "Cannot assign manager role",
            "description": "As an admin, I should be able to assign the Manager role but it's greyed out. I can assign other roles. Is Manager role restricted somehow?"
        },
    ],
    "Team Management": [
        {
            "title": "Cannot create new team",
            "description": "The 'Create Team' button does nothing when clicked. No error, just doesn't respond. I'm an admin with team management permissions."
        },
    ],
    "User Invitation Issues": [
        {
            "title": "Invitation emails not being received",
            "description": "Sent invitations to 10 new team members but none received the emails. Checked their spam folders. The invitations show as 'sent' in our admin panel."
        },
    ],
    "Deactivation Requests": [
        {
            "title": "Request to deactivate account",
            "description": "I'd like to deactivate my account. Please confirm what happens to my data and if I can reactivate later. Username: user@email.com"
        },
    ],
    "Security Audit Request": [
        {
            "title": "Need security audit report for compliance",
            "description": "Our company requires a SOC 2 Type II report for vendor compliance review. Can you provide your latest security audit documentation?"
        },
    ],
    "Compliance Questions": [
        {
            "title": "HIPAA compliance inquiry",
            "description": "We're in healthcare and need to know if your platform is HIPAA compliant. Can you provide a BAA? What PHI safeguards are in place?"
        },
    ],
    "Data Privacy": [
        {
            "title": "Questions about data retention",
            "description": "Need to understand your data retention policies. How long is customer data kept after account closure? Required for our privacy policy."
        },
    ],
    "GDPR Requests": [
        {
            "title": "GDPR data deletion request",
            "description": "Per GDPR Article 17, I request deletion of all my personal data. Email: user@email.com. Please confirm deletion within 30 days as required."
        },
    ],
    "Account Transfer": [
        {
            "title": "Transfer account to new owner",
            "description": "I'm leaving the company and need to transfer account ownership to my colleague. New owner: newowner@company.com. What's the process?"
        },
    ],
    "Account Merge": [
        {
            "title": "Need to merge two accounts",
            "description": "I accidentally created two accounts with different emails. Need to merge all data into one account. Main: main@email.com, Duplicate: other@email.com"
        },
    ],
    "Legacy System Migration": [
        {
            "title": "Migrating from version 1 to version 2",
            "description": "We're still on the legacy v1 platform and need help migrating to v2. What's involved? Will our customizations carry over?"
        },
    ],
    "Platform Switch": [
        {
            "title": "Switching from competitor - data import help",
            "description": "We're switching from CompetitorX and have 50,000 records to migrate. Do you offer migration assistance? What formats can you import?"
        },
    ],
    "Enhancement Suggestions": [
        {
            "title": "Suggestion: Keyboard shortcuts",
            "description": "Would greatly improve productivity to have keyboard shortcuts for common actions like save (Ctrl+S), new item (Ctrl+N), etc. Currently everything requires mouse."
        },
    ],
    "UI Improvements": [
        {
            "title": "Dashboard layout is cluttered",
            "description": "The new dashboard redesign is very cluttered. Important metrics are buried under folds. Please add customization options to rearrange widgets."
        },
    ],
    "Workflow Automation": [
        {
            "title": "Need automated assignment rules",
            "description": "We need ability to auto-assign tickets based on category. Currently everything goes to one queue and we manually distribute. This doesn't scale."
        },
    ],
    "Reporting Capabilities": [
        {
            "title": "Custom report builder needed",
            "description": "The pre-built reports don't cover our needs. We need a custom report builder to create our own metrics. Many competitors offer this feature."
        },
    ],
    "Browser Compatibility": [
        {
            "title": "Site broken on Safari",
            "description": "The website doesn't work properly on Safari. Buttons don't respond, forms don't submit. Works fine on Chrome. Safari 17.2 on macOS Sonoma."
        },
    ],
    "Calculation Errors": [
        {
            "title": "Total calculations are wrong",
            "description": "The invoice totals are calculating incorrectly. Sum of line items is $847 but total shows $947. This is happening on multiple invoices."
        },
    ],
    "Unclear Instructions": [
        {
            "title": "API authentication docs confusing",
            "description": "The API authentication documentation is very confusing. Not clear if I should use API keys or OAuth. Examples don't match the text. Please clarify."
        },
    ],
    "API Reference Questions": [
        {
            "title": "Rate limits not documented",
            "description": "I can't find information about API rate limits in the documentation. What are the limits per minute/hour? Different for each endpoint?"
        },
    ],
    "Tutorial Requests": [
        {
            "title": "Need video tutorial for advanced features",
            "description": "The written docs for advanced workflows are hard to follow. Would really help to have video tutorials walking through the setup step by step."
        },
    ],
    "Changelog Queries": [
        {
            "title": "Breaking changes in recent update",
            "description": "Our integration broke after your recent update but the changelog doesn't mention any breaking changes. What exactly changed in the API?"
        },
    ],
    "Onboarding Assistance": [
        {
            "title": "Need help with initial setup",
            "description": "We're new customers and struggling with initial configuration. The self-service setup wizard keeps failing. Can we get onboarding assistance call?"
        },
    ],
    "Advanced Training": [
        {
            "title": "Advanced training for power users",
            "description": "Several team members have mastered the basics and want advanced training. Do you offer workshops or certifications for power users?"
        },
    ],
    "Best Practices": [
        {
            "title": "Best practices for large team setup",
            "description": "We're rolling out to 200 users. What are best practices for permission structure, team organization, and naming conventions?"
        },
    ],
    "Use Case Guidance": [
        {
            "title": "How to implement approval workflows",
            "description": "We want to implement a multi-level approval workflow but not sure the best way to set it up. Can you provide guidance for our use case?"
        },
    ],
    "Certification Questions": [
        {
            "title": "How to get certified administrator",
            "description": "I want to become a certified administrator. What exams do I need to pass? Is there study material available? Cost of certification?"
        },
    ],
    "Volume Discounts": [
        {
            "title": "Discount for 1000+ licenses",
            "description": "We're interested in rolling out to our entire organization (1000+ users). What volume discounts are available at this scale?"
        },
    ],
    "Custom Pricing": [
        {
            "title": "Need custom pricing model",
            "description": "The standard pricing tiers don't fit our usage pattern. We have many users but low transaction volume. Can we discuss custom pricing?"
        },
    ],
    "Competitive Comparison": [
        {
            "title": "Feature comparison with CompetitorX",
            "description": "We're evaluating you against CompetitorX. Do you have a feature comparison matrix? Specifically interested in API capabilities."
        },
    ],
    "ROI Analysis": [
        {
            "title": "Need ROI data for business case",
            "description": "Building a business case for management. Do you have case studies or ROI calculators showing typical customer savings/efficiency gains?"
        },
    ],
    "License Transfer": [
        {
            "title": "Transfer license to subsidiary",
            "description": "We're spinning off a division into a separate company. Need to transfer some licenses to the new entity. What's the process?"
        },
    ],
    "Compliance Verification": [
        {
            "title": "License compliance audit",
            "description": "We want to ensure we're license compliant before year-end audit. Can you provide a report of all licenses assigned vs. purchased?"
        },
    ],
    "Usage Limits": [
        {
            "title": "Approaching API usage limit",
            "description": "Dashboard shows we're at 85% of our API call limit. We need to understand our options: optimize calls, upgrade, or purchase additional quota?"
        },
    ],
    "Enterprise Agreement": [
        {
            "title": "Enterprise agreement inquiry",
            "description": "We're interested in an enterprise agreement with consolidated billing for our 10 subsidiaries. Who can we speak with about this?"
        },
    ],
    "Terms Negotiation": [
        {
            "title": "Need modified terms for legal",
            "description": "Our legal team has concerns about some standard terms (liability limits, indemnification). Can we negotiate modified terms?"
        },
    ],
    "SLA Questions": [
        {
            "title": "SLA uptime guarantee questions",
            "description": "Your SLA mentions 99.9% uptime. How is this calculated? What are the credits for breaches? Does scheduled maintenance count against uptime?"
        },
    ],
    "Partnership Inquiries": [
        {
            "title": "Technology partnership opportunity",
            "description": "We're a complementary SaaS product and interested in integration partnership. We have 10,000+ mutual customers. Who handles partnerships?"
        },
    ],
    "Reseller Agreements": [
        {
            "title": "Interested in becoming a reseller",
            "description": "We're an IT services company interested in reselling your product. What's your reseller program? Margins? Support requirements?"
        },
    ],
}


def generate_ticket_content(level3_category: str) -> Tuple[str, str]:
    """Generate realistic ticket title and description for a category."""
    templates = TICKET_TEMPLATES.get(level3_category, [])
    
    if templates:
        template = random.choice(templates)
        title = template["title"]
        description = template["description"]
        
        # Add some variation
        if "{email}" in description:
            description = description.replace("{email}", f"user{random.randint(100,999)}@company.com")
    else:
        # Generate generic content for categories without templates
        title = f"Issue with {level3_category}"
        description = f"Customer is experiencing problems related to {level3_category}. " \
                     f"This requires investigation and resolution. " \
                     f"The issue started recently and affects their daily operations."
    
    # Add random variations
    variations = [
        "",
        " Please help urgently!",
        " This is blocking our work.",
        " Appreciate any assistance.",
        " Thank you in advance.",
        " Need resolution ASAP.",
    ]
    
    if random.random() > 0.5:
        description += random.choice(variations)
    
    return title, description


def generate_synthetic_tickets(num_tickets: int = 1000) -> List[dict]:
    """Generate synthetic tickets with classifications."""
    tickets = []
    
    # Get all categories
    all_paths = []
    for level1, level2_dict in CLASSIFICATION_HIERARCHY.items():
        for level2, level3_list in level2_dict.items():
            for level3 in level3_list:
                all_paths.append((level1, level2, level3))
    
    # Generate tickets
    for i in range(num_tickets):
        # Select random classification path
        level1, level2, level3 = random.choice(all_paths)
        
        # Generate content
        title, description = generate_ticket_content(level3)
        
        # Generate metadata
        created_at = datetime.utcnow() - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        priorities = ["low", "medium", "high", "critical"]
        priority_weights = [0.2, 0.4, 0.3, 0.1]
        
        sources = ["email", "web_form", "chat", "phone", "api", "slack", "mobile_app"]
        
        ticket = {
            "id": str(uuid4()),
            "title": title,
            "description": description,
            "priority": random.choices(priorities, weights=priority_weights)[0],
            "source": random.choice(sources),
            "customer_id": f"CUST-{random.randint(10000, 99999)}",
            "level1_category": level1,
            "level2_category": level2,
            "level3_category": level3,
            "created_at": created_at.isoformat(),
            "status": "classified",
            "is_training_data": True,
            # Metadata for learning
            "was_auto_resolved": random.random() > 0.3,
            "classification_was_correct": random.random() > 0.1,  # 90% accuracy baseline
            "resolution_time_hours": random.randint(1, 72),
        }
        
        tickets.append(ticket)
    
    return tickets


def generate_hierarchy_json() -> dict:
    """Generate the hierarchy structure for Neo4j import."""
    hierarchy = {
        "levels": 3,
        "categories": CLASSIFICATION_HIERARCHY,
        "statistics": {
            "level1_count": len(CLASSIFICATION_HIERARCHY),
            "level2_count": sum(len(v) for v in CLASSIFICATION_HIERARCHY.values()),
            "level3_count": sum(
                len(l3) 
                for l2_dict in CLASSIFICATION_HIERARCHY.values() 
                for l3 in l2_dict.values()
            ),
        }
    }
    return hierarchy


def main():
    """Generate and save synthetic data."""
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    
    # Generate tickets
    print("Generating 1000 synthetic tickets...")
    tickets = generate_synthetic_tickets(1000)
    
    # Save tickets
    tickets_file = output_dir / "synthetic_tickets.json"
    with open(tickets_file, "w") as f:
        json.dump(tickets, f, indent=2)
    print(f"Saved tickets to {tickets_file}")
    
    # Generate and save hierarchy
    hierarchy = generate_hierarchy_json()
    hierarchy_file = output_dir / "classification_hierarchy.json"
    with open(hierarchy_file, "w") as f:
        json.dump(hierarchy, f, indent=2)
    print(f"Saved hierarchy to {hierarchy_file}")
    
    # Print statistics
    print("\n=== Dataset Statistics ===")
    print(f"Total tickets: {len(tickets)}")
    print(f"Level 1 categories: {hierarchy['statistics']['level1_count']}")
    print(f"Level 2 categories: {hierarchy['statistics']['level2_count']}")
    print(f"Level 3 categories: {hierarchy['statistics']['level3_count']}")
    
    # Distribution by Level 1
    print("\n=== Distribution by Level 1 ===")
    level1_counts = {}
    for t in tickets:
        l1 = t["level1_category"]
        level1_counts[l1] = level1_counts.get(l1, 0) + 1
    
    for l1, count in sorted(level1_counts.items(), key=lambda x: -x[1]):
        print(f"  {l1}: {count} ({count/len(tickets)*100:.1f}%)")


if __name__ == "__main__":
    main()

