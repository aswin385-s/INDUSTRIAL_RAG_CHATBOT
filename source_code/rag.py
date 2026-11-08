import json
import os
import re
from dataclasses import dataclass, field

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import faiss
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

TOP_K = 3
MIN_RELEVANCE_SCORE = 0.35
MIN_KEYWORD_OVERLAP = 0.35

FALLBACK = "I could not find this in the provided documents."

SYSTEM_PROMPT = f"""
You are an industrial maintenance assistant for plant operators
and maintenance engineers.

Answer questions using ONLY the supplied excerpts from the
provided industrial pump manual.

Rules:
1. Every factual statement must be supported by the excerpts.
2. Never guess or use outside knowledge.
3. Never invent warranty periods, prices, specifications, or procedures.
4. Preserve numerical values and units exactly as written.
5. Give concise, direct answers.
6. Include relevant safety warnings from the excerpts.
7. The troubleshooting guide lists separate "Problem:" entries.
   Use the causes and remedies only from the entry whose problem
   matches the question. Never combine them with another entry.
8. If the excerpts do not contain enough evidence to answer,
   reply exactly:
   "{FALLBACK}"
"""


def normalize(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s.-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_keywords(text):
    stopwords = {
        "a", "an", "the", "is", "are", "was", "were", "be",
        "been", "being", "do", "does", "did", "what", "which",
        "who", "when", "where", "why", "how", "can", "could",
        "would", "should", "will", "may", "might", "to", "of",
        "in", "on", "at", "for", "from", "with", "and", "or",
        "it", "this", "that", "these", "those", "i", "we",
        "you", "me", "my", "our", "your", "please", "tell",
        "explain", "give", "about", "much", "many", "maximum",
        "minimum", "show", "provide", "provided", "according",
        "manual", "document", "documents"
    }

    return {
        word
        for word in (w.strip(".-") for w in normalize(text).split())
        if word not in stopwords and len(word) > 1
    }


CLARIFY = (
    "I could not tell what that refers to. "
    "Please ask the full question."
)

QUANTITY_NOUNS = {
    "temperature", "value", "limit", "pressure", "speed", "rate",
    "level", "figure", "number", "voltage", "power", "flow", "head",
    "size", "period", "interval", "rating"
}

MAX_FOLLOW_UP_WORDS = 12

FOLLOW_UP_PHRASES = {
    "what about it",
    "what about that",
    "how can i prevent it",
    "how to prevent it",
    "why does it happen",
    "what is the limit",
    "tell me more",
    "explain more"
}

UNIT_ALIASES = {
    "celsius": ("celsius", "°c"),
    "fahrenheit": ("fahrenheit", "°f"),
    "bar": ("bar",),
    "rpm": ("rpm",),
    "kw": ("kw", "kilowatt", "kilowatts"),
    "volt": ("v", "volt", "volts"),
    "mm": ("mm", "millimeter", "millimeters", "millimetre", "millimetres"),
}

_UNIT_LOOKUP = {
    alias: key
    for key, aliases in UNIT_ALIASES.items()
    for alias in aliases
}

_DEMONSTRATIVE = re.compile(
    r"\b(?:that|this|those|these|the same)\s+([A-Za-z]+)\b(.*)$",
    re.IGNORECASE
)

_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")


def _stem(word):
    word = word.lower()
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def _numbers(text):
    return frozenset(_NUMBER.findall(text or ""))


def requested_unit(tail):
    match = re.match(
        r"^(?:in|as|using|expressed in|converted to)\s+(.+)$",
        tail.strip(),
        re.IGNORECASE
    )

    if not match:
        return None

    word = match.group(1).lower()
    word = re.sub(r"\bdegrees?\b", "", word)
    word = word.replace(" ", "").strip(" ?.!")

    return _UNIT_LOOKUP.get(word)


def find_quantity(text, unit_key):
    aliases = sorted(UNIT_ALIASES[unit_key], key=len, reverse=True)
    pattern = (
        r"(\d+(?:\.\d+)?)\s*(?:degrees?\s*)?(?:"
        + "|".join(re.escape(alias) for alias in aliases)
        + r")(?![A-Za-z])"
    )
    match = re.search(pattern, text or "", re.IGNORECASE)

    if not match:
        return None

    return match.group(1), match.group(0).strip()


REMEDY_WORDS = {
    "prevent", "prevention", "avoid", "fix", "remedy", "remedies",
    "solution", "solve", "resolve", "repair", "stop", "correct"
}
CAUSE_WORDS = {"cause", "causes", "caused", "reason", "reasons", "why"}

ENTRY_TITLE_COVERAGE = 0.6
ENTRY_ANSWER_COVERAGE = 0.6


def _root(word):
    return word.lower()[:6]


def entry_title(text):
    match = re.search(r"Problem:\s*(.+?)\.(?:\s|$)", text)
    return match.group(1).strip() if match else None


def entry_field(text, pattern):
    match = re.search(pattern + r":\s*(.+?)\.(?:\s|$)", text)
    return match.group(1).strip() if match else None


def question_intent(question):
    words = set(normalize(question).split())
    asks_cause = bool(words & CAUSE_WORDS)
    asks_remedy = bool(words & REMEDY_WORDS)

    if asks_cause and asks_remedy:
        return "both"
    if asks_cause:
        return "cause"
    if asks_remedy:
        return "remedy"
    return None


@dataclass
class ResolvedQuestion:
    text: str
    is_follow_up: bool = False
    dangling: bool = False
    restated_answer: str = None
    anchor_numbers: frozenset = field(default_factory=frozenset)
    intent_text: str = None

    def __post_init__(self):
        if self.intent_text is None:
            self.intent_text = self.text


class IndustrialChatbot:

    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.base_dir = base_dir

        self.index_path = os.path.join(
            base_dir, "vector_store", "index.faiss"
        )
        self.chunks_path = os.path.join(
            base_dir, "vector_store", "chunks.json"
        )

        if not os.path.isfile(self.index_path):
            raise FileNotFoundError(
                f"FAISS index not found: {self.index_path}. "
                "Run ingest.py first."
            )

        if not os.path.isfile(self.chunks_path):
            raise FileNotFoundError(
                f"Chunk file not found: {self.chunks_path}. "
                "Run ingest.py first."
            )

        print("Loading FAISS index...")

        self.index = faiss.read_index(self.index_path)

        with open(self.chunks_path, "r", encoding="utf-8") as file:
            chunks = json.load(file)

        if isinstance(chunks, dict):
            chunks = chunks.get("chunks", [])

        if not isinstance(chunks, list):
            raise ValueError(
                "Unexpected chunks.json format. "
                "Expected a list of document chunks."
            )

        if len(chunks) != self.index.ntotal:
            raise ValueError(
                f"Index contains {self.index.ntotal} vectors, "
                f"but chunks.json contains {len(chunks)} chunks. "
                "Run ingest.py again to rebuild the vector store."
            )

        self.chunks = chunks

        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL
        )

        print("Loading language model...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            LLM_MODEL
        )

        self.llm = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True
        )

        self.llm.to("cpu")
        self.llm.eval()

        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("Chatbot is ready.")

    @staticmethod
    def _chunk_text(chunk):
        if isinstance(chunk, str):
            return chunk

        if isinstance(chunk, dict):
            for key in ("text", "content", "chunk"):
                if chunk.get(key) is not None:
                    return str(chunk[key])

        return ""

    @staticmethod
    def _chunk_source(chunk):
        if isinstance(chunk, dict):
            return str(
                chunk.get(
                    "source",
                    chunk.get("filename", "Unknown source")
                )
            )

        return "Unknown source"

    @staticmethod
    def _chunk_id(chunk, default_id):
        if isinstance(chunk, dict):
            return chunk.get("chunk_id", default_id)

        return default_id

    def retrieve(self, question, k=TOP_K):
        if not question.strip() or self.index.ntotal == 0:
            return []

        k = max(1, min(int(k), self.index.ntotal))

        query_embedding = self.embedding_model.encode(
            [question],
            normalize_embeddings=True,
            convert_to_numpy=True
        ).astype("float32")

        scores, indices = self.index.search(
            query_embedding, k
        )

        hits = []

        for score, index_id in zip(scores[0], indices[0]):
            if index_id < 0 or index_id >= len(self.chunks):
                continue

            chunk = self.chunks[int(index_id)]
            text = self._chunk_text(chunk)

            if not text.strip():
                continue

            hits.append({
                "text": text,
                "score": float(score),
                "source": self._chunk_source(chunk),
                "chunk_id": self._chunk_id(
                    chunk, int(index_id)
                )
            })

        return hits

    def resolve_follow_up(
        self, question, previous_question=None, previous_answer=None
    ):
        question = question.strip()
        plain = ResolvedQuestion(text=question)

        previous_usable = bool(previous_question) and (
            previous_answer is None
            or previous_answer.strip() not in (FALLBACK, CLARIFY)
        )

        if previous_usable:
            earlier = _DEMONSTRATIVE.search(previous_question)
            if earlier and earlier.group(1).lower() in QUANTITY_NOUNS:
                previous_usable = False

        normalized = normalize(question)

        if normalized in FOLLOW_UP_PHRASES:
            if not previous_usable:
                return plain

            text = f"Previous question: {previous_question}\n"

            if previous_answer:
                text += (
                    "Previous answer (context only, not evidence): "
                    f"{previous_answer}\n"
                )

            text += f"Follow-up question: {question}"

            return ResolvedQuestion(
                text=text, is_follow_up=True, intent_text=question
            )

        match = _DEMONSTRATIVE.search(question)

        if (
            not match
            or match.group(1).lower() not in QUANTITY_NOUNS
            or len(normalized.split()) > MAX_FOLLOW_UP_WORDS
        ):
            return plain

        noun = match.group(1).lower()
        tail = match.group(2).strip(" ?.!")

        previous_words = {
            _stem(word) for word in normalize(previous_question or "").split()
        }

        if not previous_usable or _stem(noun) not in previous_words:
            return ResolvedQuestion(text=question, dangling=True)

        base = previous_question.strip().rstrip("?. !")

        if tail and normalize(tail) not in normalize(base):
            standalone = f"{base} {tail}?"
        else:
            standalone = f"{base}?"

        restated = None
        unit = requested_unit(tail)

        if unit and previous_answer:
            quantity = find_quantity(previous_answer, unit)

            if quantity:
                value, shown = quantity
                symbol = f" ({value}°C)" if unit == "celsius" else ""
                restated = (
                    f"The {noun} is {shown}{symbol}, "
                    "as stated in the previous answer."
                )

        return ResolvedQuestion(
            text=standalone,
            is_follow_up=True,
            restated_answer=restated,
            anchor_numbers=_numbers(previous_answer),
        )

    def _focus_hits(self, question, hits, intent_question=None):
        if question_intent(intent_question or question) is None:
            return hits, None

        question_roots = {_root(w) for w in get_keywords(question)}
        best, best_coverage = None, 0.0

        for hit in hits:
            title = entry_title(hit["text"])

            if not title:
                continue

            title_roots = {_root(w) for w in get_keywords(title)}

            if not title_roots:
                continue

            coverage = len(title_roots & question_roots) / len(title_roots)

            if coverage > best_coverage:
                best, best_coverage = hit, coverage

        if best is None or best_coverage < ENTRY_TITLE_COVERAGE:
            return hits, None

        return [best], best

    @staticmethod
    def _extract_answer(entry, question):
        title = entry_title(entry["text"])
        intent = question_intent(question)

        if not title or intent is None:
            return None

        causes = entry_field(entry["text"], r"Causes?")
        remedy = entry_field(entry["text"], r"Remedy")
        parts = []

        if intent in ("cause", "both") and causes:
            parts.append(f"Causes of {title.lower()}: {causes}.")

        if intent in ("remedy", "both") and remedy:
            parts.append(f"Remedy for {title.lower()}: {remedy}.")

        return " ".join(parts) if parts else None

    def _has_relevant_context(self, question, hits):
        if not hits:
            return False

        best_score = max(
            hit["score"] for hit in hits
        )

        if best_score < MIN_RELEVANCE_SCORE:
            return False

        retrieved_text = " ".join(
            hit["text"] for hit in hits
        )
        retrieved_keywords = get_keywords(retrieved_text)

        if not retrieved_keywords:
            return False

        question_parts = [
            part.strip()
            for part in question.splitlines()
            if part.strip()
        ]

        for part in question_parts:
            question_keywords = get_keywords(part)

            if not question_keywords:
                continue

            overlap = (
                len(question_keywords & retrieved_keywords)
                / len(question_keywords)
            )

            if overlap >= MIN_KEYWORD_OVERLAP:
                return True

        return False

    def _has_evidence_for_question(self, question, hits):
        if not hits:
            return False

        context = normalize(
            " ".join(hit["text"] for hit in hits)
        )
        question = normalize(question)

        if not context:
            return False

        evidence_requirements = {
            "warranty": ("warranty", "guarantee"),
            "guarantee": ("warranty", "guarantee"),
            "price": ("price", "cost", "rupees", "inr"),
            "cost": ("price", "cost", "rupees", "inr"),
            "viscosity": ("viscosity",),
            "gearbox": ("gearbox",)
        }

        question_words = set(question.split())

        for requested_term, evidence_terms in (
            evidence_requirements.items()
        ):
            if requested_term in question_words:
                if not any(
                    term in context
                    for term in evidence_terms
                ):
                    return False

        return True

    def generate_answer(self, question, hits):
        if not hits:
            return FALLBACK

        excerpts = "\n\n".join(
            f"[Excerpt {number}]\n{hit['text']}"
            for number, hit in enumerate(hits, start=1)
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Manual excerpts:\n{excerpts}\n\n"
                    f"Question: {question}\n\n"
                    "Answer using only the supplied evidence. "
                    "If the evidence is insufficient, return "
                    f"exactly: {FALLBACK}"
                )
            }
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        )

        with torch.inference_mode():
            output = self.llm.generate(
                **inputs,
                max_new_tokens=160,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

        new_tokens = output[0][
            inputs["input_ids"].shape[1]:
        ]

        answer = self.tokenizer.decode(
            new_tokens,
            skip_special_tokens=True
        ).strip()

        if not answer:
            return FALLBACK

        if normalize(FALLBACK) in normalize(answer):
            return FALLBACK

        return answer

    def validate_answer(
        self, answer, question, hits, entry=None, intent_question=None
    ):
        if not answer or not hits:
            return FALLBACK

        if normalize(FALLBACK) in normalize(answer):
            return FALLBACK

        context = normalize(
            " ".join(hit["text"] for hit in hits)
        )
        normalized_answer = normalize(answer)

        if not context:
            return FALLBACK

        answer_numbers = set(
            re.findall(r"\b\d+(?:\.\d+)?\b", answer)
        )
        context_numbers = set(
            re.findall(r"\b\d+(?:\.\d+)?\b", context)
        )

        if not answer_numbers.issubset(context_numbers):
            return FALLBACK

        technical_terms = {
            "warranty", "guarantee", "price", "cost",
            "voltage", "pressure", "temperature", "rpm",
            "overheating", "bearing", "impeller",
            "mechanical seal", "lubrication", "maintenance",
            "gearbox", "viscosity", "flow rate", "head"
        }

        answer_terms = {
            term for term in technical_terms
            if term in normalized_answer
        }
        context_terms = {
            term for term in technical_terms
            if term in context
        }

        if not answer_terms.issubset(context_terms):
            return FALLBACK

        if entry is not None:
            entry_roots = {
                _root(word) for word in normalize(entry["text"]).split()
            }
            answer_roots = {
                _root(word) for word in get_keywords(answer)
            } - {
                _root(word)
                for word in get_keywords(intent_question or question)
            }

            if answer_roots:
                covered = len(answer_roots & entry_roots) / len(answer_roots)

                if covered < ENTRY_ANSWER_COVERAGE:
                    return FALLBACK

            intent = question_intent(intent_question or question)
            title_roots = {
                _root(word)
                for word in get_keywords(entry_title(entry["text"]) or "")
            }
            wanted = {
                "cause": entry_field(entry["text"], r"Causes?"),
                "remedy": entry_field(entry["text"], r"Remedy"),
            }

            if intent in wanted and all(wanted.values()):
                own = answer_roots - title_roots

                if own:
                    def share(field):
                        roots = {
                            _root(word) for word in normalize(field).split()
                        }
                        return len(own & roots) / len(own)

                    other = "remedy" if intent == "cause" else "cause"

                    if (
                        share(wanted[intent]) < ENTRY_ANSWER_COVERAGE
                        or share(wanted[intent]) <= share(wanted[other])
                    ):
                        return FALLBACK

        normalized_question = normalize(question)

        if (
            "warranty" in normalized_question
            or "guarantee" in normalized_question
        ):
            if not re.search(
                r"\b(warranty|guarantee)\b",
                context
            ):
                return FALLBACK

        return answer

    @staticmethod
    def _enforce_anchor(answer, resolved):
        if (
            answer == FALLBACK
            or not resolved.is_follow_up
            or not resolved.anchor_numbers
        ):
            return answer

        answer_numbers = _numbers(answer)

        if answer_numbers and not (
            answer_numbers & resolved.anchor_numbers
        ):
            return FALLBACK

        return answer

    def answer(
        self,
        question,
        k=TOP_K,
        previous_question=None,
        previous_answer=None
    ):
        question = question.strip()

        if not question:
            return FALLBACK, []

        resolved = self.resolve_follow_up(
            question,
            previous_question,
            previous_answer
        )

        if resolved.dangling:
            return CLARIFY, []

        hits = self.retrieve(resolved.text, k)

        if resolved.restated_answer:
            return resolved.restated_answer, hits

        if not self._has_relevant_context(resolved.text, hits):
            return FALLBACK, hits

        if not self._has_evidence_for_question(
            resolved.text, hits
        ):
            return FALLBACK, hits

        context_hits, entry = self._focus_hits(
            resolved.text, hits, resolved.intent_text
        )

        generated_answer = self.generate_answer(
            resolved.text, context_hits
        )

        validated_answer = self.validate_answer(
            generated_answer,
            resolved.text,
            context_hits,
            entry,
            resolved.intent_text
        )

        if entry is not None and validated_answer == FALLBACK:
            grounded = self._extract_answer(entry, resolved.intent_text)

            if grounded:
                validated_answer = grounded

        return self._enforce_anchor(validated_answer, resolved), hits