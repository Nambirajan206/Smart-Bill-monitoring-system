import os
import logging
import json

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    import google.genai as genai
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        MODEL_ID = "models/gemini-2.0-flash-exp"
        logger.info("Gemini client initialized successfully")
    else:
        client = None
        logger.warning("GEMINI_API_KEY not found - AI features will use fallback responses")
except ImportError:
    client = None
    logger.warning("google.genai not installed - AI features will use fallback responses")
except Exception as e:
    client = None
    logger.error(f"Failed to initialize Gemini client: {e}")

def generate_initial_analysis(analysis_data):
    """Generate initial analysis report using Gemini AI."""
    if client is None:
        return generate_fallback_analysis(analysis_data)

    try:
        summary = analysis_data.get('summary', {})
        anomalies = analysis_data.get('anomalies', [])

        prompt = f"""
You are an electricity usage analyzer for a power distribution company.

**Analysis Rules:**
- Residential bills: Normal range is ₹500 - ₹5000
- Bills below ₹500 are unusually low
- Bills above ₹5000 are abnormally high
- Commercial properties are excluded from anomaly detection

**Data Summary:**
- Total Houses Analyzed: {summary.get('total_records', 0)}
- Residential Houses: {summary['residential'].get('count', 0)}
- Commercial Properties: {summary['commercial'].get('count', 0)}
- Anomalies Detected: {summary.get('anomalies_count', 0)}

**Residential Statistics:**
- Avg: ₹{summary['residential'].get('mean', 0):.2f}
- Median: ₹{summary['residential'].get('median', 0):.2f}
- Max: ₹{summary['residential'].get('max', 0):.2f}
- Min: ₹{summary['residential'].get('min', 0):.2f}

**Commercial Statistics:**
- Count: {summary['commercial'].get('count', 0)}
- Avg: ₹{summary['commercial'].get('mean', 0):.2f}
- Max: ₹{summary['commercial'].get('max', 0):.2f}

**Top Anomalies (sample):**
{format_anomalies_for_prompt(anomalies[:20])}

Provide a comprehensive analysis with:
1. Overview of usage patterns
2. Key findings
3. Severity comparison (high vs low bills)
4. Reasons for anomalies
5. Actionable recommendations
"""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )

        return response.text

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return generate_fallback_analysis(analysis_data)

def answer_question(question, context):
    """Answer user questions using Gemini AI with full context awareness."""
    if client is None:
        return generate_fallback_answer(question, context)

    try:
        summary = context.get('summary', {})
        anomalies = context.get('anomalies', [])

        prompt = f"""
You are an electricity usage analyzer assistant. Answer the user's question based ONLY on the provided data.

**Data Summary:**
- Total Records: {summary.get('total_records', 0)}
- Residential: {summary['residential'].get('count', 0)} houses
- Commercial: {summary['commercial'].get('count', 0)} properties
- Anomalies: {summary.get('anomalies_count', 0)}

**Residential Stats:**
- Avg: ₹{summary['residential'].get('mean', 0):.2f}
- Median: ₹{summary['residential'].get('median', 0):.2f}
- Max: ₹{summary['residential'].get('max', 0):.2f}
- Min: ₹{summary['residential'].get('min', 0):.2f}
- Std Dev: ₹{summary['residential'].get('std', 0):.2f}

**Commercial Stats:**
- Avg: ₹{summary['commercial'].get('mean', 0):.2f}
- Max: ₹{summary['commercial'].get('max', 0):.2f}

**Thresholds:**
- Residential Normal Range: ₹{summary['thresholds'].get('residential_min', 500)} - ₹{summary['thresholds'].get('residential_max', 5000)}

**All Anomalies:**
{format_anomalies_for_prompt(anomalies)}

**User Question:**
{question}

**Instructions:**
- If asked about a specific house (e.g., "House 46", "house id 3"), search the anomaly list and provide ALL details for that house
- If asked about counts, use the summary statistics
- If asked about recommendations, provide specific actionable advice
- If the data doesn't contain the answer, say so clearly
- Be specific with numbers and house IDs when relevant
"""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )

        return response.text

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return generate_fallback_answer(question, context)

def format_anomalies_for_prompt(anomalies):
    """Format anomalies list for AI prompt."""
    if not anomalies:
        return "No anomalies detected."

    lines = []
    for i, a in enumerate(anomalies[:100], 1):
        lines.append(
            f"{i}. House {a['house_id']} ({a.get('address', 'N/A')}) - "
            f"Month: {a.get('month', 'N/A')}, Bill: ₹{a['bill_amount']:.2f}, "
            f"Units: {a.get('units_consumed', 0)}, Severity: {a['severity']}, "
            f"Reason: {a['reason']}"
        )
    
    if len(anomalies) > 100:
        lines.append(f"... and {len(anomalies) - 100} more anomalies")
    
    return "\n".join(lines)

def generate_fallback_analysis(analysis_data):
    """Generate analysis when Gemini is unavailable."""
    summary = analysis_data.get('summary', {})
    anomalies = analysis_data.get('anomalies', [])
    
    res = summary.get('residential', {})
    com = summary.get('commercial', {})
    
    high_count = sum(1 for a in anomalies if a['severity'] == 'high')
    low_count = sum(1 for a in anomalies if a['severity'] == 'low')
    
    return f"""Electricity Usage Analysis Report

1. Overview
Analyzed {summary.get('total_records', 0)} properties ({res.get('count', 0)} residential, {com.get('count', 0)} commercial).

2. Residential Statistics
- Average Bill: ₹{res.get('mean', 0):.2f}
- Median Bill: ₹{res.get('median', 0):.2f}
- Range: ₹{res.get('min', 0):.2f} - ₹{res.get('max', 0):.2f}
- Normal Range: ₹{summary['thresholds'].get('residential_min', 500)} - ₹{summary['thresholds'].get('residential_max', 5000)}

3. Anomalies Detected
Total: {summary.get('anomalies_count', 0)} ({(summary.get('anomalies_count', 0) / res.get('count', 1) * 100):.1f}% of residential)
- High Bills (>₹5000): {high_count}
- Low Bills (<₹500): {low_count}

4. Key Findings
{'- Significant anomaly rate requiring investigation' if summary.get('anomalies_count', 0) > res.get('count', 1) * 0.1 else '- Low anomaly rate indicates healthy consumption patterns'}
- Maximum residential bill of ₹{res.get('max', 0):.2f} is {'nearly ' + str(int(res.get('max', 0) / 5000)) + 'x' if res.get('max', 0) > 10000 else 'above'} the normal threshold

5. Recommendations
- Investigate houses with multiple anomalies across different months
- For high bills: Check meter accuracy, offer energy audits
- For low bills: Inspect for meter tampering, verify occupancy
- Prioritize properties with extreme values (>₹15,000 or <₹300)

Use the chat to ask specific questions about individual houses or get detailed insights.
"""

def generate_fallback_answer(question, context):
    """Generate fallback answer when Gemini is unavailable."""
    q_lower = question.lower()
    summary = context.get('summary', {})
    anomalies = context.get('anomalies', [])
    res = summary.get('residential', {})
    com = summary.get('commercial', {})
    
    import re
    house_match = re.search(r'\b(?:house\s+(?:id\s+)?)?(\d+)\b', q_lower)
    
    if house_match:
        house_id = house_match.group(1)
        house_anomalies = [a for a in anomalies if str(a['house_id']) == house_id]
        
        if house_anomalies:
            lines = [f"House {house_id} - {len(house_anomalies)} anomalies found:\n"]
            for a in house_anomalies:
                lines.append(
                    f"• {a['month']}: ₹{a['bill_amount']:.2f} ({a['units_consumed']} units) - "
                    f"{a['severity'].upper()} - {a['reason']}"
                )
            lines.append(f"\nAddress: {house_anomalies[0].get('address', 'N/A')}")
            return "\n".join(lines)
        else:
            return f"House {house_id} has no anomalies detected. All bills fall within the normal residential range (₹500 - ₹5000)."
    
    if 'how many' in q_lower and 'anomal' in q_lower:
        return f"I detected {summary.get('anomalies_count', 0)} anomalies out of {res.get('count', 0)} residential houses, which is {(summary.get('anomalies_count', 0) / res.get('count', 1) * 100):.1f}% of the residential properties."
    
    elif 'inspect' in q_lower or 'priority' in q_lower or 'first' in q_lower:
        house_counts = {}
        for a in anomalies:
            hid = a['house_id']
            house_counts[hid] = house_counts.get(hid, 0) + 1
        
        top_houses = sorted(house_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        lines = ["Houses to inspect first (by number of anomalies):\n"]
        for hid, count in top_houses:
            house_data = [a for a in anomalies if a['house_id'] == hid]
            max_bill = max(a['bill_amount'] for a in house_data)
            lines.append(f"• House {hid}: {count} anomalies, highest bill ₹{max_bill:.2f}")
        
        return "\n".join(lines)
    
    elif 'residential' in q_lower or 'commercial' in q_lower:
        return (
            f"Residential: {res.get('count', 0)} houses, Avg ₹{res.get('mean', 0):.2f}, "
            f"Range ₹{res.get('min', 0):.2f} - ₹{res.get('max', 0):.2f}\n"
            f"Commercial: {com.get('count', 0)} properties, Avg ₹{com.get('mean', 0):.2f}, "
            f"Max ₹{com.get('max', 0):.2f}"
        )
    
    elif 'recommend' in q_lower or 'what should' in q_lower:
        high_count = sum(1 for a in anomalies if a['severity'] == 'high')
        low_count = sum(1 for a in anomalies if a['severity'] == 'low')
        
        return (
            f"Recommendations:\n\n"
            f"1. High Bills ({high_count} cases): Conduct meter accuracy checks and offer energy audits\n"
            f"2. Low Bills ({low_count} cases): Inspect for meter tampering and verify occupancy\n"
            f"3. Priority: Focus on houses with multiple anomalies across different months\n"
            f"4. Extreme Cases: Any residential bill >₹15,000 or <₹300 needs immediate investigation"
        )
    
    elif 'low' in q_lower and ('bill' in q_lower or 'meter' in q_lower):
        low_anomalies = [a for a in anomalies if a['severity'] == 'low']
        return (
            f"{len(low_anomalies)} low-bill anomalies detected (bills <₹500).\n"
            f"Lowest: ₹{min(a['bill_amount'] for a in low_anomalies):.2f}\n\n"
            f"These may indicate:\n"
            f"• Meter malfunction or tampering\n"
            f"• Vacant properties\n"
            f"• Electricity theft\n\n"
            f"Recommend immediate physical meter inspections."
        )
    
    else:
        return (
            f"Based on the analysis:\n\n"
            f"• Total Records: {summary.get('total_records', 0)}\n"
            f"• Residential: {res.get('count', 0)} (Avg ₹{res.get('mean', 0):.2f})\n"
            f"• Commercial: {com.get('count', 0)} (Avg ₹{com.get('mean', 0):.2f})\n"
            f"• Anomalies: {summary.get('anomalies_count', 0)}\n\n"
            f"Ask me about specific houses (e.g., 'House 46 bill'), recommendations, or statistics!"
        )

def validate_gemini_config():
    """Check if Gemini is properly configured."""
    if client is None:
        return {
            "valid": False,
            "error": "Gemini client not initialized. Check GEMINI_API_KEY environment variable."
        }
    
    try:
        test = client.models.generate_content(
            model=MODEL_ID,
            contents="Test message"
        )
        return {
            "valid": True,
            "message": "Gemini API working correctly",
            "model": MODEL_ID
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }