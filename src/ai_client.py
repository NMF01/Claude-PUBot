"""Claude AI integration for motivational messages."""
import threading
from typing import Callable, Optional

_anthropic_ok = False
try:
    import anthropic as _anthropic_mod
    _anthropic_ok = True
except ImportError:
    pass

_FALLBACKS = [
    "Every step forward, no matter how small, brings you closer to your goal. Keep going!",
    "Focus on progress, not perfection. You're doing great — one task at a time.",
    "The secret of getting ahead is getting started. You've already begun — stay with it.",
    "Consistency is the key to achievement. Keep your eyes on those three tasks.",
    "You have the power to make today count. Stay committed to what matters most.",
    "Small daily improvements lead to stunning long-term results. Keep pushing!",
    "Your focused effort today is building the tomorrow you want. Stay strong!",
    "One task at a time, one step at a time. You've got this — stay the course.",
]

_FALLBACKS_HE = [
    "כל צעד קדימה, גם הקטן ביותר, מקרב אותך למטרה. המשך!",
    "התמקד בהתקדמות, לא בשלמות. אתה עושה עבודה נהדרת — משימה אחת בכל פעם.",
    "הסוד להצלחה הוא להתחיל. כבר התחלת — המשך איתו.",
    "עקביות היא המפתח להישגים. שמור את עיניך על שלוש המשימות.",
    "יש לך את הכוח לגרום להיום להשפיע. הישאר מחויב למה שחשוב.",
    "שיפורים יומיומיים קטנים מובילים לתוצאות מרשימות לטווח הארוך. המשך לדחוף!",
    "המאמץ הממוקד שלך היום בונה את המחר שאתה רוצה. תישאר חזק!",
    "משימה אחת בכל פעם, צעד אחד בכל פעם. אתה יכול — הישאר במסלול.",
]


class AIClient:
    def __init__(self, api_key: str = ''):
        self.api_key = api_key
        self._client = None
        self._cycle = 0

    def update_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if not _anthropic_ok or not self.api_key:
            return None
        if not self._client:
            try:
                self._client = _anthropic_mod.Anthropic(api_key=self.api_key)
            except Exception:
                pass
        return self._client

    def get_motivational_message(
        self,
        tasks: list[str],
        completed: list[bool],
        callback: Callable[[str, Optional[str]], None],
        lang: str = 'en',
    ) -> None:
        """Asynchronously fetch a motivational message, then call callback(msg, err)."""

        def _fetch():
            try:
                client = self._get_client()
                if not client:
                    callback(self._fallback(lang), None)
                    return

                done_count = sum(completed)
                lines = '\n'.join(
                    f"  {i+1}. {t} [{'DONE' if c else 'in progress'}]"
                    for i, (t, c) in enumerate(zip(tasks, completed))
                )
                prompt = (
                    "You are a warm, encouraging productivity coach. "
                    f"The user's focus tasks for today are:\n{lines}\n\n"
                    f"Progress: {done_count}/{len(tasks)} completed.\n\n"
                    "Write a brief (1–2 sentences, 30–70 words) motivational message. "
                    "Reference their specific tasks where natural. "
                    "Be genuine and specific — not generic. "
                    "No quotes, no markdown, just the message."
                )
                if lang == 'he':
                    prompt += (
                        "\n\nRespond entirely in Hebrew (עברית). "
                        "Use natural, warm Israeli Hebrew."
                    )
                response = client.messages.create(
                    model='claude-opus-4-6',
                    max_tokens=150,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                callback(response.content[0].text.strip(), None)
            except Exception as exc:
                callback(self._fallback(lang), str(exc))

        threading.Thread(target=_fetch, daemon=True).start()

    def _fallback(self, lang: str = 'en') -> str:
        pool = _FALLBACKS_HE if lang == 'he' else _FALLBACKS
        msg = pool[self._cycle % len(pool)]
        self._cycle += 1
        return msg
