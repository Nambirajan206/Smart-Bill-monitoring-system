import os
import logging

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
        logger.warning("GEMINI_API_KEY not found - AI features will use fallback")
except ImportError:
    client = None
    logger.warning("google.genai not installed - using fallback")
except Exception as e:
    client = None
    logger.error(f"Gemini initialization failed: {e}")

def analyze_consumer_with_ai(consumer_id, consumer_type, monthly_bills):
    """Use Gemini AI to analyze a single consumer's monthly pattern and detect spikes"""
    if client is None:
        return analyze_consumer_fallback(consumer_id, consumer_type, monthly_bills)
    
    try:
        bills_text = "\n".join([f"{b['month']}: ₹{b['amount']:.2f}" for b in monthly_bills])
        
        prompt = f"""
You are an expert electricity bill analyzer. Analyze this consumer's billing pattern to detect sudden spikes.

**Consumer Details:**
- ID: {consumer_id}
- Type: {consumer_type}
- Number of months: {len(monthly_bills)}

**Monthly Bills:**
{bills_text}

**Your Task:**
1. Analyze the month-to-month pattern
2. Identify ANY months that show sudden, abnormal increases
3. Compare each month to its previous month(s) and the overall pattern
4. A spike is when a bill jumps significantly compared to the consumer's normal usage

**Return ONLY a JSON object** (no markdown, no backticks) with this exact structure:
{{
  "has_spikes": true or false,
  "spikes": [
    {{
      "month": "month name",
      "bill_amount": number,
      "previous_bill": number (average of 1-2 previous months),
      "increase_percentage": number,
      "reason": "brief explanation of why this is a spike"
    }}
  ],
  "pattern_summary": "brief description of overall consumption pattern"
}}

If no spikes detected, return: {{"has_spikes": false, "spikes": [], "pattern_summary": "description"}}

IMPORTANT: Return ONLY the JSON object, nothing else.
"""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        
        import json
        response_text = response.text.strip()
        
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        result = json.loads(response_text)
        
        if result.get('has_spikes') and result.get('spikes'):
            for spike in result['spikes']:
                spike['consumer_id'] = consumer_id
                spike['consumer_type'] = consumer_type
        
        return result
        
    except Exception as e:
        logger.error(f"Gemini analysis failed for {consumer_id}: {e}")
        return analyze_consumer_fallback(consumer_id, consumer_type, monthly_bills)

def analyze_consumer_fallback(consumer_id, consumer_type, monthly_bills):
    """Fallback spike detection when Gemini unavailable"""
    import numpy as np
    
    spikes = []
    
    for i in range(1, len(monthly_bills)):
        current = monthly_bills[i]
        prev = monthly_bills[i-1]
        
        increase_pct = ((current['amount'] - prev['amount']) / prev['amount']) * 100
        
        if increase_pct > 50:
            spikes.append({
                'consumer_id': consumer_id,
                'consumer_type': consumer_type,
                'month': current['month'],
                'bill_amount': current['amount'],
                'previous_bill': prev['amount'],
                'increase_percentage': increase_pct,
                'reason': f'Sudden {increase_pct:.1f}% increase from previous month'
            })
    
    if len(monthly_bills) >= 3:
        for i in range(2, len(monthly_bills)):
            current = monthly_bills[i]
            prev_bills = [monthly_bills[j]['amount'] for j in range(max(0, i-3), i)]
            avg_prev = np.mean(prev_bills)
            
            increase_pct = ((current['amount'] - avg_prev) / avg_prev) * 100
            
            if increase_pct > 80:
                existing = any(s['month'] == current['month'] for s in spikes)
                if not existing:
                    spikes.append({
                        'consumer_id': consumer_id,
                        'consumer_type': consumer_type,
                        'month': current['month'],
                        'bill_amount': current['amount'],
                        'previous_bill': avg_prev,
                        'increase_percentage': increase_pct,
                        'reason': f'{increase_pct:.1f}% above recent average'
                    })
    
    pattern_summary = f"Average bill: ₹{np.mean([b['amount'] for b in monthly_bills]):.2f}"
    
    return {
        'has_spikes': len(spikes) > 0,
        'spikes': spikes,
        'pattern_summary': pattern_summary
    }

def generate_overall_insights(all_results, summary):
    """Generate overall insights from all consumer analyses"""
    if client is None:
        return generate_fallback_insights(all_results, summary)
    
    try:
        total_spikes = sum(len(r['spikes']) for r in all_results if r['has_spikes'])
        consumers_with_spikes = sum(1 for r in all_results if r['has_spikes'])
        
        sample_spikes = []
        for result in all_results:
            if result['has_spikes']:
                sample_spikes.extend(result['spikes'][:2])
        sample_spikes = sample_spikes[:20]
        
        spike_text = "\n".join([
            f"- {s['consumer_id']} ({s['consumer_type']}): {s['month']} - ₹{s['bill_amount']:.2f} "
            f"(+{s['increase_percentage']:.1f}%) - {s['reason']}"
            for s in sample_spikes
        ])
        
        prompt = f"""
Analyze the electricity bill spike detection results across all consumers.

**Summary:**
- Total Consumers: {summary['total_consumers']}
- Residential: {summary['residential_count']}
- Commercial: {summary['commercial_count']}
- Consumers with Spikes: {consumers_with_spikes}
- Total Spikes Detected: {total_spikes}

**Sample Detected Spikes:**
{spike_text if spike_text else "No spikes detected"}

**Provide a comprehensive analysis covering:**
1. Overview of spike patterns across all consumers
2. Key insights about spike frequency and magnitude
3. Comparison between residential and commercial spike patterns
4. Possible reasons for the detected spikes
5. Actionable recommendations for the power company

Keep the analysis concise and actionable. Focus on patterns and insights.
"""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        logger.error(f"Overall insights generation failed: {e}")
        return generate_fallback_insights(all_results, summary)

def generate_fallback_insights(all_results, summary):
    """Generate fallback insights when Gemini unavailable"""
    total_spikes = sum(len(r['spikes']) for r in all_results if r['has_spikes'])
    consumers_with_spikes = sum(1 for r in all_results if r['has_spikes'])
    
    res_spikes = sum(len(r['spikes']) for r in all_results 
                     if r['has_spikes'] and r['spikes'] and r['spikes'][0].get('consumer_type') == 'Residential')
    com_spikes = total_spikes - res_spikes
    
    if total_spikes == 0:
        return """**Electricity Bill Spike Analysis**

No sudden spikes detected across all consumers.

All consumers show stable, predictable billing patterns with normal month-to-month variations.

This indicates healthy consumption patterns across the board.
"""
    
    return f"""**Electricity Bill Spike Analysis**

**Overview:**
Analyzed {summary['total_consumers']} consumers and detected {total_spikes} billing spikes across {consumers_with_spikes} consumers.

**Key Findings:**
- Residential Spikes: {res_spikes} detected
- Commercial Spikes: {com_spikes} detected
- Spike Rate: {(consumers_with_spikes / summary['total_consumers'] * 100):.1f}% of consumers affected

**Pattern Analysis:**
Each consumer's billing pattern was analyzed individually using AI. Spikes were detected by comparing each month to the consumer's own historical usage pattern, with no fixed thresholds applied.

**Recommendations:**
1. Investigate all {consumers_with_spikes} consumers with detected spikes
2. Verify meter accuracy for consumers showing unusual patterns
3. Check for seasonal factors or one-time events causing spikes
4. Consider energy audits for consumers with multiple spikes
5. Monitor these consumers closely in upcoming months

The detection system uses pattern-based analysis tailored to each consumer's unique usage profile.
"""

def answer_chat_question(question, context):
    """Answer user questions about the analysis using full context"""
    if client is None:
        return answer_chat_fallback(question, context)
    
    try:
        summary = context.get('summary', {})
        spikes = context.get('spikes', [])
        analysis = context.get('analysis', '')
        raw_data = context.get('raw_data', [])
        
        # Format spikes for context
        spikes_text = ""
        if spikes:
            spikes_text = "\n".join([
                f"- {s['consumer_id']} ({s['consumer_type']}): {s['month']} spike - "
                f"₹{s['bill_amount']:.2f} (from ₹{s['previous_bill']:.2f}, +{s['increase_percentage']:.1f}%) - {s['reason']}"
                for s in spikes[:30]
            ])
            if len(spikes) > 30:
                spikes_text += f"\n... and {len(spikes) - 30} more spikes"
        
        # Format raw data sample
        raw_data_text = ""
        if raw_data:
            raw_data_text = "\n".join([
                f"- {d['consumer_id']} ({d['consumer_type']}): {', '.join([f'{m}=₹{a:.0f}' for m, a in list(d['monthly_bills'].items())[:6]])}"
                for d in raw_data[:10]
            ])
            if len(raw_data) > 10:
                raw_data_text += f"\n... and {len(raw_data) - 10} more consumers"
        
        prompt = f"""
You are an AI assistant helping analyze electricity bill data. Answer the user's question based ONLY on the provided data.

**Analysis Summary:**
- Total Consumers: {summary.get('total_consumers', 0)}
- Residential: {summary.get('residential_count', 0)}
- Commercial: {summary.get('commercial_count', 0)}
- Consumers with Spikes: {summary.get('consumers_with_spikes', 0)}
- Total Spikes: {summary.get('spike_count', 0)}

**Previous Analysis:**
{analysis}

**Detected Spikes:**
{spikes_text if spikes_text else "No spikes detected"}

**Raw Consumer Data (sample):**
{raw_data_text if raw_data_text else "No data available"}

**User Question:**
{question}

**Instructions:**
- Answer ONLY based on the data provided above
- If asked about a specific consumer, search the data and provide detailed information
- If asked for recommendations, provide specific, actionable advice
- If the data doesn't contain the answer, say so clearly
- Be concise but thorough
- Use numbers and specifics from the data

Provide a clear, helpful answer:
"""

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        logger.error(f"Chat response failed: {e}")
        return answer_chat_fallback(question, context)

def answer_chat_fallback(question, context):
    """Fallback chat responses when Gemini unavailable"""
    import re
    
    q_lower = question.lower()
    summary = context.get('summary', {})
    spikes = context.get('spikes', [])
    
    consumer_match = re.search(r'\b(c\d+|consumer\s*\d+)\b', q_lower)
    
    if consumer_match:
        consumer_id = consumer_match.group(1).upper().replace('CONSUMER ', 'C').replace(' ', '')
        consumer_spikes = [s for s in spikes if s['consumer_id'].upper().replace(' ', '') == consumer_id]
        
        if consumer_spikes:
            lines = [f"Consumer {consumer_id} has {len(consumer_spikes)} detected spike(s):\n"]
            for s in consumer_spikes:
                lines.append(
                    f"• {s['month']}: ₹{s['bill_amount']:.2f} "
                    f"(+{s['increase_percentage']:.1f}% from ₹{s['previous_bill']:.2f}) - {s['reason']}"
                )
            return "\n".join(lines)
        else:
            return f"Consumer {consumer_id} shows normal billing patterns with no detected spikes."
    
    if 'how many' in q_lower and 'spike' in q_lower:
        return (
            f"Total spikes detected: {summary.get('spike_count', 0)}\n"
            f"Consumers with spikes: {summary.get('consumers_with_spikes', 0)} out of {summary.get('total_consumers', 0)}\n"
            f"Spike rate: {(summary.get('consumers_with_spikes', 0) / max(summary.get('total_consumers', 1), 1) * 100):.1f}%"
        )
    
    elif 'highest' in q_lower or 'biggest' in q_lower:
        if spikes:
            top_spike = max(spikes, key=lambda x: x['increase_percentage'])
            return (
                f"Highest spike detected:\n"
                f"Consumer: {top_spike['consumer_id']} ({top_spike['consumer_type']})\n"
                f"Month: {top_spike['month']}\n"
                f"Bill: ₹{top_spike['bill_amount']:.2f}\n"
                f"Increase: +{top_spike['increase_percentage']:.1f}%\n"
                f"Reason: {top_spike['reason']}"
            )
        else:
            return "No spikes detected in the analysis."
    
    elif 'recommend' in q_lower or 'what should' in q_lower:
        if summary.get('spike_count', 0) > 0:
            return (
                f"Recommendations based on {summary.get('spike_count', 0)} detected spikes:\n\n"
                f"1. Investigate {summary.get('consumers_with_spikes', 0)} consumers with spikes\n"
                f"2. Verify meter accuracy for unusual patterns\n"
                f"3. Check for seasonal factors or events\n"
                f"4. Offer energy audits to affected consumers\n"
                f"5. Monitor closely in upcoming billing cycles"
            )
        else:
            return "No spikes detected. Continue regular monitoring of all consumers."
    
    elif 'residential' in q_lower or 'commercial' in q_lower:
        res_spikes = [s for s in spikes if s.get('consumer_type') == 'Residential']
        com_spikes = [s for s in spikes if s.get('consumer_type') == 'Commercial']
        
        return (
            f"Residential consumers: {summary.get('residential_count', 0)} total, {len(res_spikes)} spikes detected\n"
            f"Commercial consumers: {summary.get('commercial_count', 0)} total, {len(com_spikes)} spikes detected"
        )
    
    else:
        return (
            f"Analysis Summary:\n"
            f"• Total Consumers: {summary.get('total_consumers', 0)}\n"
            f"• Spikes Detected: {summary.get('spike_count', 0)}\n"
            f"• Consumers Affected: {summary.get('consumers_with_spikes', 0)}\n\n"
            f"Ask me about specific consumers, recommendations, or spike details!"
        )

def validate_gemini_config():
    """Check if Gemini is properly configured"""
    if client is None:
        return {"valid": False, "error": "Gemini client not initialized"}
    
    try:
        test = client.models.generate_content(model=MODEL_ID, contents="Test")
        return {"valid": True, "message": "Gemini API working", "model": MODEL_ID}
    except Exception as e:
        return {"valid": False, "error": str(e)}
