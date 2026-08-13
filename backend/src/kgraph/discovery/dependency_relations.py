import re
from typing import List, Optional

import spacy
from spacy.tokens import Doc, Span, Token

from kgraph.discovery.schemas import DiscoveredRelation

DEFAULT_DETERMINERS = ("the", "a", "an")


class DependencyRelationExtractor:
    """Extract relations between subjects/objects via the dependency tree.

    No LLM and no predefined taxonomy: for each predicate verb in a sentence we
    take its subject (``nsubj``/``nsubjpass``), its object (``dobj`` or the
    object of a prepositional modifier) and derive the relation label from the
    verb lemma plus the preposition (e.g. "obtained from", "reported to").
    """

    def __init__(
        self,
        model: str = "en_core_web_sm",
        determiners: list[str] | None = None,
    ):
        self.nlp = spacy.load(model)

        dets = sorted(
            set(DEFAULT_DETERMINERS) | set(determiners or []),
            key=len,
            reverse=True,
        )
        self._leading_det = re.compile(
            r"^(" + "|".join(map(re.escape, dets)) + r")\s+",
            re.IGNORECASE,
        )

    def extract(self, doc: str) -> List[DiscoveredRelation]:
        relations: list[DiscoveredRelation] = []
        seen: set[tuple[str, str, str]] = set()
        for sent in self.nlp(doc).sents:
            chunks = {ch.root.i: ch for ch in sent.noun_chunks}
            root = sent.root
            if root.pos_ != "VERB":
                continue
            for verb in self._verbs(root):
                subj = self._subject(verb, root)
                if subj is None:
                    continue
                for source, relation, target in self._verb_relations(subj, verb, chunks):
                    key = (source.lower(), relation, target.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    relations.append(
                        DiscoveredRelation(
                            source=source,
                            relation=relation,
                            target=target,
                            evidence=sent.text,
                        )
                    )
        return relations

    @staticmethod
    def _verbs(root: Token) -> List[Token]:
        """Root verb plus verb complements/conjuncts (e.g. 'began charging', 'disputed ... but responded')."""
        verbs = [root]
        for child in root.children:
            if child.dep_ in ("xcomp", "ccomp", "conj") and child.pos_ == "VERB":
                verbs.append(child)
        return verbs

    @staticmethod
    def _subject(verb: Token, root: Token) -> Optional[Token]:
        subj = next(
            (c for c in verb.children if c.dep_ in ("nsubj", "nsubjpass")), None
        )
        if subj is not None:
            return subj
        if verb is root:
            return None
        return next(
            (c for c in root.children if c.dep_ in ("nsubj", "nsubjpass")), None
        )

    def _verb_relations(
        self,
        subj: Token,
        verb: Token,
        chunks: dict[int, Span],
    ) -> List[tuple[str, str, str]]:
        children = list(verb.children)
        dobj = next((c for c in children if c.dep_ == "dobj"), None)
        if dobj is None:
            dobj = next((c for c in children if c.dep_ == "attr"), None)

        def pobj_of(prep: Token) -> Optional[Token]:
            return next((c for c in prep.children if c.dep_ == "pobj"), None)

        preps = []
        for prep in children:
            if prep.dep_ != "prep":
                continue
            pobj = pobj_of(prep)
            if pobj is not None and not self._is_pronoun(pobj):
                preps.append((prep, pobj))

        named_preps = [
            (prep, pobj) for prep, pobj in preps if self._is_named(pobj)
        ]
        subj_pronoun = self._is_pronoun(subj)
        subj_text = self._span_text(subj, chunks)

        relations: list[tuple[str, str, str]] = []

        def add(src: Optional[str], label: str, tgt: Optional[str]) -> None:
            if src and tgt:
                relations.append((src, label, tgt))

        if subj_pronoun:
            if dobj is None or self._is_pronoun(dobj):
                return relations
            src = self._span_text(dobj, chunks)
            for prep, pobj in named_preps:
                add(src, f"{verb.lemma_} {prep.text.lower()}", self._span_text(pobj, chunks))
            return relations

        if dobj is not None and not self._is_pronoun(dobj):
            add(subj_text, verb.lemma_, self._span_text(dobj, chunks))
            for prep, pobj in self._preps_of(dobj):
                if prep.text.lower() != "of":
                    add(subj_text, f"{verb.lemma_} {prep.text.lower()}", self._span_text(pobj, chunks))

        if named_preps or dobj is None:
            active = named_preps if named_preps else preps
            for prep, pobj in active:
                add(subj_text, f"{verb.lemma_} {prep.text.lower()}", self._span_text(pobj, chunks))
        return relations

    @staticmethod
    def _preps_of(head: Token) -> List[tuple[Token, Token]]:
        result = []
        for child in head.children:
            if child.dep_ != "prep":
                continue
            pobj = next((c for c in child.children if c.dep_ == "pobj"), None)
            if pobj is not None:
                result.append((child, pobj))
        return result

    def _is_pronoun(self, tok: Token) -> bool:
        return tok.pos_ == "PRON"

    @staticmethod
    def _is_named(tok: Token) -> bool:
        return tok.pos_ == "PROPN" or tok.ent_type_ != ""

    def _span_text(self, head: Token, chunks: dict[int, Span]) -> str:
        chunk = chunks.get(head.i)
        text = chunk.text if chunk is not None else head.text
        text = self._leading_det.sub("", text).strip()
        return text
