"""Optional commentary on computed evidence; never a source of metric calculations."""
import json
import logging
from typing import Literal
from urllib.parse import quote
import requests
from pydantic import BaseModel, Field, ConfigDict
from app.config import settings

Provider = Literal['rules', 'gemini', 'groq', 'openrouter']
logger = logging.getLogger(__name__)


class Commentary(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: str = Field(min_length=1, max_length=2000)
    review_questions: list[str] = Field(min_length=1, max_length=5)
    practice_exercise: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(max_length=10)


def providers():
    return [
        {'id': 'rules', 'name': 'Local rules — no API key', 'configured': True, 'model': None,
         'url': None, 'note': 'Computed locally. No trade data sent to an LLM.'},
        {'id': 'gemini', 'name': 'Google Gemini', 'configured': bool(settings.GEMINI_API_KEY), 'model': settings.GEMINI_MODEL,
         'url': 'https://ai.google.dev/gemini-api/docs/pricing',
         'note': 'Free tier for eligible models/accounts. Unpaid-service content may be used to improve Google products.'},
        {'id': 'groq', 'name': 'Groq', 'configured': bool(settings.GROQ_API_KEY), 'model': settings.GROQ_MODEL,
         'url': 'https://console.groq.com/docs/rate-limits',
         'note': 'Free plan has model-specific quotas. Verify account limits and data controls.'},
        {'id': 'openrouter', 'name': 'OpenRouter free models', 'configured': bool(settings.OPENROUTER_API_KEY), 'model': settings.OPENROUTER_MODEL,
         'url': 'https://openrouter.ai/docs/api_reference/limits',
         'note': 'Free model availability and quotas vary. Underlying providers have separate data policies.'},
    ]


def add_commentary(report, provider: Provider = 'rules'):
    report['llm'] = {'status': 'not_requested', 'provider': 'rules', 'message': 'Local rules only.'}
    if provider == 'rules':
        return report
    config = next(p for p in providers() if p['id'] == provider)
    fallback = {'status': 'unavailable', 'provider': provider, 'model': config['model'],
                'message': 'Optional LLM review unavailable. The complete local assessment is shown.'}
    report['llm'] = fallback
    if not config['configured']:
        fallback['message'] = f'Configure {provider.upper()}_API_KEY in backend/.env to enable this reviewer. Local assessment is complete.'
        return report
    if provider == 'openrouter' and not (settings.OPENROUTER_MODEL == 'openrouter/free' or settings.OPENROUTER_MODEL.endswith(':free')):
        fallback['message'] = 'OpenRouter reviewer only allows openrouter/free or a :free model. Local assessment is complete.'
        return report
    # Only numeric aggregates and application-generated identifiers; no notes, symbols,
    # filenames, account identifiers, dates, or user-supplied labels leave the server.
    ids = [f['id'] for f in report['strengths'] + report['weaknesses']]
    payload_data = {'metrics': report['metrics'], 'coverage': report['coverage'],
                    'source': report['source'], 'finding_ids': ids, 'excluded_open': report['excluded_open']}
    prompt = (
        'You are a constructive trading-journal reviewer. Use ONLY the supplied computed evidence. '
        'Do not recalculate or invent data, diagnose psychology, infer stop violations, recommend assets, '
        'or prescribe risk percentages. No taxes or brokerage. These may be aggregate report rows, '
        'not independent trades. Small samples do not establish an edge. Null metrics are unavailable, not zero. '
        'Offer questions and a measurable practice exercise, not confident causes or guarantees. '
        'Themes: probabilistic evaluation (Douglas), defined risk and records (Elder), deliberate self-review '
        '(Steenbarger). Do not invent quotations or claim to have read books. '
        'Return JSON only: summary (string), review_questions (1-5 strings), practice_exercise (string), '
        'evidence_ids (subset of supplied finding_ids). Data: ' + json.dumps(payload_data, allow_nan=False)
    )
    try:
        if provider == 'gemini':
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{quote(settings.GEMINI_MODEL, safe="")}:generateContent',
                headers={'x-goog-api-key': settings.GEMINI_API_KEY},
                json={'contents': [{'parts': [{'text': prompt}]}],
                      'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 1600}},
                timeout=(5, 25))
            response.raise_for_status()
            content = ''.join(p.get('text', '') for p in response.json()['candidates'][0]['content']['parts'] if not p.get('thought'))
        else:
            url, key = (('https://api.groq.com/openai/v1/chat/completions', settings.GROQ_API_KEY)
                        if provider == 'groq' else ('https://openrouter.ai/api/v1/chat/completions', settings.OPENROUTER_API_KEY))
            response = requests.post(url, headers={'Authorization': f'Bearer {key}'},
                json={'model': config['model'], 'messages': [{'role': 'user', 'content': prompt}],
                      'response_format': {'type': 'json_object'}, 'max_tokens': 1600}, timeout=(5, 25))
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
        result = Commentary.model_validate_json(content)
        if any(key not in ids for key in result.evidence_ids) or any(len(q) > 1000 for q in result.review_questions):
            raise ValueError('Unsupported commentary evidence or length')
        report['llm'] = {'status': 'success', 'provider': provider, 'model': config['model'],
                         'message': 'Optional AI interpretation; computed findings above remain authoritative.',
                         **result.model_dump()}
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        # Never log the exception URL: a provider may echo credentials/request content.
        logger.warning('Optional %s reviewer failed; keeping deterministic report', provider)
    return report
