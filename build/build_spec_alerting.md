============================================================
AFH — BUILD SPEC ADDENDUM
ALERT TRANSPORT POLICY (v0.7)
============================================================

PURPOSE
-------
Define alert delivery behavior for pipeline failures
in a cost-disciplined, operator-friendly manner.

============================================================
PRIMARY ALERT CHANNEL (LOCKED)
============================================================

CHANNEL
-------
Email

RATIONALE
---------
- Free
- Reliable
- Universally available
- Works with GitHub Actions natively
- No third-party dependencies required

REQUIREMENTS
------------
- Alerts sent ONLY on:
  • pipeline abort
  • integrity check failure
- One alert per failed run
- Include:
  • run date
  • failure stage
  • pointer to logs directory

============================================================
SECONDARY ALERT CHANNEL (OPTIONAL)
============================================================

CHANNEL
-------
SMS (opportunistic)

STATUS
------
OPTIONAL
NON-REQUIRED
BEST-EFFORT ONLY

RULES
-----
- SMS MAY be used IF AND ONLY IF:
  • a free tier exists
  • no credit card is required
  • no paid usage can be triggered accidentally
- SMS is a DUPLICATE of email, not a replacement
- SMS failure must NEVER fail the pipeline

EXAMPLES (NON-BINDING)
---------------------
- Free-tier notification services
- Email-to-SMS gateways (carrier dependent)

============================================================
COST DISCIPLINE RULE
============================================================

AFH will NOT:
- Pay for SMS
- Subscribe to monitoring platforms
- Add alerting complexity

If SMS cannot be delivered for free:
→ Email remains the sole alert channel.

============================================================
DESIGN INTENT
============================================================

Alerts exist to:
- Notify the operator of FAILURE
- Enable manual inspection

Alerts do NOT exist to:
- Provide diagnostics
- Create dashboards
- Trigger automated remediation

============================================================
END ALERT TRANSPORT POLICY
============================================================

