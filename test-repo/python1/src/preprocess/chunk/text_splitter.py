# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/6 17:44
# @Author  : cuils
# @Description:
朴素分块方式 copy from langchain
"""

"""
From: https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters
"""
import re
import copy
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeVar,
    Union,
    TypedDict,
    cast,
    Collection,
    Callable,
    Iterable,
    Sequence,
    Set as AbstractSet
)

from typing_extensions import Self, override


try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False

try:
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False


try:
    # Type ignores needed as long as sentence-transformers doesn't support Python 3.14.
    from sentence_transformers import (  # type: ignore[import-not-found, unused-ignore]
        SentenceTransformer,
    )

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)

TS = TypeVar("TS", bound="TextSplitter")


class TextSplitter(ABC):
    """Interface for splitting text into chunks."""

    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Callable[[str], int] = len,
        keep_separator: bool | Literal["start", "end"] = False,  # noqa: FBT001,FBT002
        add_start_index: bool = False,  # noqa: FBT001,FBT002
        strip_whitespace: bool = True,  # noqa: FBT001,FBT002
    ) -> None:
        """Create a new TextSplitter.

        Args:
            chunk_size: Maximum size of chunks to return
            chunk_overlap: Overlap in characters between chunks
            length_function: Function that measures the length of given chunks
            keep_separator: Whether to keep the separator and where to place it
                in each corresponding chunk `(True='start')`
            add_start_index: If `True`, includes chunk's start index in metadata
            strip_whitespace: If `True`, strips whitespace from the start and end of
                every document
        """
        if chunk_size <= 0:
            msg = f"chunk_size must be > 0, got {chunk_size}"
            raise ValueError(msg)
        if chunk_overlap < 0:
            msg = f"chunk_overlap must be >= 0, got {chunk_overlap}"
            raise ValueError(msg)
        if chunk_overlap > chunk_size:
            msg = (
                f"Got a larger chunk overlap ({chunk_overlap}) than chunk size "
                f"({chunk_size}), should be smaller."
            )
            raise ValueError(msg)
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function
        self._keep_separator = keep_separator
        self._add_start_index = add_start_index
        self._strip_whitespace = strip_whitespace

    @abstractmethod
    def split_text(self, text: str) -> list[str]:
        """Split text into multiple components."""

    def create_documents(self, texts: list[str]):
        """Create a list of `Document` objects from a list of texts."""
        chunks = []
        for i, text in enumerate(texts):
            index = 0
            previous_chunk_len = 0
            for chunk in self.split_text(text):
                if self._add_start_index:
                    offset = index + previous_chunk_len - self._chunk_overlap
                    index = text.find(chunk, max(0, offset))
                    previous_chunk_len = len(chunk)
                chunks.append(chunk)
        return chunks

    def split_documents(self, texts: Iterable[str]) -> list[str]:
        """Split documents."""
        return self.create_documents(texts)

    def _join_docs(self, docs: list[str], separator: str) -> str | None:
        text = separator.join(docs)
        if self._strip_whitespace:
            text = text.strip()
        return text or None

    def _merge_splits(self, splits: Iterable[str], separator: str) -> list[str]:
        # We now want to combine these smaller pieces into medium size
        # chunks to send to the LLM.
        separator_len = self._length_function(separator)

        docs = []
        current_doc: list[str] = []
        total = 0
        for d in splits:
            len_ = self._length_function(d)
            if (
                total + len_ + (separator_len if len(current_doc) > 0 else 0)
                > self._chunk_size
            ):
                if total > self._chunk_size:
                    logger.warning(
                        "Created a chunk of size %d, which is longer than the "
                        "specified %d",
                        total,
                        self._chunk_size,
                    )
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    # Keep on popping if:
                    # - we have a larger chunk than in the chunk overlap
                    # - or if we still have any chunks and the length is long
                    while total > self._chunk_overlap or (
                        total + len_ + (separator_len if len(current_doc) > 0 else 0)
                        > self._chunk_size
                        and total > 0
                    ):
                        total -= self._length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        current_doc = current_doc[1:]
            current_doc.append(d)
            total += len_ + (separator_len if len(current_doc) > 1 else 0)
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        return docs

    @classmethod
    def from_huggingface_tokenizer(
        cls, tokenizer: PreTrainedTokenizerBase, **kwargs: Any
    ) -> "TextSplitter":
        """Text splitter that uses Hugging Face tokenizer to count length."""
        if not _HAS_TRANSFORMERS:
            msg = (
                "Could not import transformers python package. "
                "Please install it with `pip install transformers`."
            )
            raise ValueError(msg)

        if not isinstance(tokenizer, PreTrainedTokenizerBase):
            msg = "Tokenizer received was not an instance of PreTrainedTokenizerBase"  # type: ignore[unreachable]
            raise ValueError(msg)  # noqa: TRY004

        def _huggingface_tokenizer_length(text: str) -> int:
            return len(tokenizer.tokenize(text))

        return cls(length_function=_huggingface_tokenizer_length, **kwargs)

    @classmethod
    def from_tiktoken_encoder(
        cls,
        encoding_name: str = "gpt2",
        model_name: str | None = None,
        allowed_special: Literal["all"] | AbstractSet[str] = set(),
        disallowed_special: Literal["all"] | Collection[str] = "all",
        **kwargs: Any,
    ) -> Self:
        """Text splitter that uses `tiktoken` encoder to count length."""
        if not _HAS_TIKTOKEN:
            msg = (
                "Could not import tiktoken python package. "
                "This is needed in order to calculate max_tokens_for_prompt. "
                "Please install it with `pip install tiktoken`."
            )
            raise ImportError(msg)

        if model_name is not None:
            enc = tiktoken.encoding_for_model(model_name)
        else:
            enc = tiktoken.get_encoding(encoding_name)

        def _tiktoken_encoder(text: str) -> int:
            return len(
                enc.encode(
                    text,
                    allowed_special=allowed_special,
                    disallowed_special=disallowed_special,
                )
            )

        if issubclass(cls, TokenTextSplitter):
            extra_kwargs = {
                "encoding_name": encoding_name,
                "model_name": model_name,
                "allowed_special": allowed_special,
                "disallowed_special": disallowed_special,
            }
            kwargs = {**kwargs, **extra_kwargs}

        return cls(length_function=_tiktoken_encoder, **kwargs)

    @override
    def transform_documents(
        self, documents: Sequence[str], **kwargs: Any
    ) -> Sequence[str]:
        """Transform sequence of documents by splitting them."""
        return self.split_documents(list(documents))


class TokenTextSplitter(TextSplitter):
    """Splitting text to tokens using model tokenizer."""

    def __init__(
        self,
        encoding_name: str = "gpt2",
        model_name: str | None = None,
        allowed_special: set | None = None,
        disallowed_special: Literal["all"] | Collection[str] = "all",
        **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(**kwargs)
        if allowed_special is None:
            allowed_special = set()
        if not _HAS_TIKTOKEN:
            msg = (
                "Could not import tiktoken python package. "
                "This is needed in order to for TokenTextSplitter. "
                "Please install it with `pip install tiktoken`."
            )
            raise ImportError(msg)

        if model_name is not None:
            enc = tiktoken.encoding_for_model(model_name)
        else:
            enc = tiktoken.get_encoding(encoding_name)
        self._tokenizer = enc
        self._allowed_special = allowed_special
        self._disallowed_special = disallowed_special

    def split_text(self, text: str) -> list[str]:
        """Splits the input text into smaller chunks based on tokenization.

        This method uses a custom tokenizer configuration to encode the input text
        into tokens, processes the tokens in chunks of a specified size with overlap,
        and decodes them back into text chunks. The splitting is performed using the
        `split_text_on_tokens` function.

        Args:
            text: The input text to be split into smaller chunks.

        Returns:
            A list of text chunks, where each chunk is derived from a portion
                of the input text based on the tokenization and chunking rules.
        """

        def _encode(_text: str) -> list[int]:
            return self._tokenizer.encode(
                _text,
                allowed_special=self._allowed_special,
                disallowed_special=self._disallowed_special,
            )

        tokenizer = Tokenizer(
            chunk_overlap=self._chunk_overlap,
            tokens_per_chunk=self._chunk_size,
            decode=self._tokenizer.decode,
            encode=_encode,
        )

        return split_text_on_tokens(text=text, tokenizer=tokenizer)


class Language(str, Enum):
    """Enum of the programming languages."""

    CPP = "cpp"
    GO = "go"
    JAVA = "java"
    KOTLIN = "kotlin"
    JS = "js"
    TS = "ts"
    PHP = "php"
    PROTO = "proto"
    PYTHON = "python"
    RST = "rst"
    RUBY = "ruby"
    RUST = "rust"
    SCALA = "scala"
    SWIFT = "swift"
    MARKDOWN = "markdown"
    LATEX = "latex"
    HTML = "html"
    SOL = "sol"
    CSHARP = "csharp"
    COBOL = "cobol"
    C = "c"
    LUA = "lua"
    PERL = "perl"
    HASKELL = "haskell"
    ELIXIR = "elixir"
    POWERSHELL = "powershell"
    VISUALBASIC6 = "visualbasic6"


@dataclass(frozen=True)
class Tokenizer:
    """Tokenizer data class."""

    chunk_overlap: int
    """Overlap in tokens between chunks"""
    tokens_per_chunk: int
    """Maximum number of tokens per chunk"""
    decode: Callable[[list[int]], str]
    """ Function to decode a list of token IDs to a string"""
    encode: Callable[[str], list[int]]
    """ Function to encode a string to a list of token IDs"""


def split_text_on_tokens(*, text: str, tokenizer: Tokenizer) -> list[str]:
    """Split incoming text and return chunks using tokenizer."""
    splits: list[str] = []
    input_ids = tokenizer.encode(text)
    start_idx = 0
    if tokenizer.tokens_per_chunk <= tokenizer.chunk_overlap:
        msg = "tokens_per_chunk must be greater than chunk_overlap"
        raise ValueError(msg)

    while start_idx < len(input_ids):
        cur_idx = min(start_idx + tokenizer.tokens_per_chunk, len(input_ids))
        chunk_ids = input_ids[start_idx:cur_idx]
        if not chunk_ids:
            break
        decoded = tokenizer.decode(chunk_ids)
        if decoded:
            splits.append(decoded)
        if cur_idx == len(input_ids):
            break
        start_idx += tokenizer.tokens_per_chunk - tokenizer.chunk_overlap
    return splits


class CharacterTextSplitter(TextSplitter):
    """Splitting text that looks at characters."""

    def __init__(
        self,
        separator: str = "\n\n",
        is_separator_regex: bool = False,  # noqa: FBT001,FBT002
        **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(**kwargs)
        self._separator = separator
        self._is_separator_regex = is_separator_regex

    def split_text(self, text: str) -> list[str]:
        """Split into chunks without re-inserting lookaround separators."""
        # 1. Determine split pattern: raw regex or escaped literal
        sep_pattern = (
            self._separator if self._is_separator_regex else re.escape(self._separator)
        )

        # 2. Initial split (keep separator if requested)
        splits = _split_text_with_regex(
            text, sep_pattern, keep_separator=self._keep_separator
        )

        # 3. Detect zero-width lookaround so we never re-insert it
        lookaround_prefixes = ("(?=", "(?<!", "(?<=", "(?!")
        is_lookaround = self._is_separator_regex and any(
            self._separator.startswith(p) for p in lookaround_prefixes
        )

        # 4. Decide merge separator:
        #    - if keep_separator or lookaround -> don't re-insert
        #    - else -> re-insert literal separator
        merge_sep = ""
        if not (self._keep_separator or is_lookaround):
            merge_sep = self._separator

        # 5. Merge adjacent splits and return
        return self._merge_splits(splits, merge_sep)


def _split_text_with_regex(
    text: str, separator: str, *, keep_separator: bool | Literal["start", "end"]
) -> list[str]:
    # Now that we have the separator, split the text
    if separator:
        if keep_separator:
            # The parentheses in the pattern keep the delimiters in the result.
            splits_ = re.split(f"({separator})", text)
            splits = (
                ([splits_[i] + splits_[i + 1] for i in range(0, len(splits_) - 1, 2)])
                if keep_separator == "end"
                else ([splits_[i] + splits_[i + 1] for i in range(1, len(splits_), 2)])
            )
            if len(splits_) % 2 == 0:
                splits += splits_[-1:]
            splits = (
                ([*splits, splits_[-1]])
                if keep_separator == "end"
                else ([splits_[0], *splits])
            )
        else:
            splits = re.split(separator, text)
    else:
        splits = list(text)
    return [s for s in splits if s]


class RecursiveCharacterTextSplitter(TextSplitter):
    """Splitting text by recursively look at characters.

    Recursively tries to split by different characters to find one
    that works.
    """

    def __init__(
        self,
        separators: list[str] | None = None,
        keep_separator: bool | Literal["start", "end"] = True,  # noqa: FBT001,FBT002
        is_separator_regex: bool = False,  # noqa: FBT001,FBT002
        **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or ["\n\n", "\n", " ", ""]
        self._is_separator_regex = is_separator_regex

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Split incoming text and return chunks."""
        final_chunks = []
        # Get appropriate separator to use
        separator = separators[-1]
        new_separators = []
        for i, _s in enumerate(separators):
            separator_ = _s if self._is_separator_regex else re.escape(_s)
            if not _s:
                separator = _s
                break
            if re.search(separator_, text):
                separator = _s
                new_separators = separators[i + 1 :]
                break

        separator_ = separator if self._is_separator_regex else re.escape(separator)
        splits = _split_text_with_regex(
            text, separator_, keep_separator=self._keep_separator
        )

        # Now go merging things, recursively splitting longer texts.
        good_splits = []
        separator_ = "" if self._keep_separator else separator
        for s in splits:
            if self._length_function(s) < self._chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged_text = self._merge_splits(good_splits, separator_)
                    final_chunks.extend(merged_text)
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    other_info = self._split_text(s, new_separators)
                    final_chunks.extend(other_info)
        if good_splits:
            merged_text = self._merge_splits(good_splits, separator_)
            final_chunks.extend(merged_text)
        return final_chunks

    def split_text(self, text: str) -> list[str]:
        """Split the input text into smaller chunks based on predefined separators.

        Args:
            text: The input text to be split.

        Returns:
            A list of text chunks obtained after splitting.
        """
        return self._split_text(text, self._separators)

    @classmethod
    def from_language(
        cls, language: Language, **kwargs: Any
    ) -> "RecursiveCharacterTextSplitter":
        """Return an instance of this class based on a specific language.

        This method initializes the text splitter with language-specific separators.

        Args:
            language: The language to configure the text splitter for.
            **kwargs: Additional keyword arguments to customize the splitter.

        Returns:
            An instance of the text splitter configured for the specified language.
        """
        separators = cls.get_separators_for_language(language)
        return cls(separators=separators, is_separator_regex=True, **kwargs)

    @staticmethod
    def get_separators_for_language(language: Language) -> list[str]:
        """Retrieve a list of separators specific to the given language.

        Args:
            language: The language for which to get the separators.

        Returns:
            A list of separators appropriate for the specified language.
        """
        if language in {Language.C, Language.CPP}:
            return [
                # Split along class definitions
                "\nclass ",
                # Split along function definitions
                "\nvoid ",
                "\nint ",
                "\nfloat ",
                "\ndouble ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nswitch ",
                "\ncase ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.GO:
            return [
                # Split along function definitions
                "\nfunc ",
                "\nvar ",
                "\nconst ",
                "\ntype ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nswitch ",
                "\ncase ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.JAVA:
            return [
                # Split along class definitions
                "\nclass ",
                # Split along method definitions
                "\npublic ",
                "\nprotected ",
                "\nprivate ",
                "\nstatic ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nswitch ",
                "\ncase ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.KOTLIN:
            return [
                # Split along class definitions
                "\nclass ",
                # Split along method definitions
                "\npublic ",
                "\nprotected ",
                "\nprivate ",
                "\ninternal ",
                "\ncompanion ",
                "\nfun ",
                "\nval ",
                "\nvar ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nwhen ",
                "\ncase ",
                "\nelse ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.JS:
            return [
                # Split along function definitions
                "\nfunction ",
                "\nconst ",
                "\nlet ",
                "\nvar ",
                "\nclass ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nswitch ",
                "\ncase ",
                "\ndefault ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.TS:
            return [
                "\nenum ",
                "\ninterface ",
                "\nnamespace ",
                "\ntype ",
                # Split along class definitions
                "\nclass ",
                # Split along function definitions
                "\nfunction ",
                "\nconst ",
                "\nlet ",
                "\nvar ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nswitch ",
                "\ncase ",
                "\ndefault ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.PHP:
            return [
                # Split along function definitions
                "\nfunction ",
                # Split along class definitions
                "\nclass ",
                # Split along control flow statements
                "\nif ",
                "\nforeach ",
                "\nwhile ",
                "\ndo ",
                "\nswitch ",
                "\ncase ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.PROTO:
            return [
                # Split along message definitions
                "\nmessage ",
                # Split along service definitions
                "\nservice ",
                # Split along enum definitions
                "\nenum ",
                # Split along option definitions
                "\noption ",
                # Split along import statements
                "\nimport ",
                # Split along syntax declarations
                "\nsyntax ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.PYTHON:
            return [
                # First, try to split along class definitions
                "\nclass ",
                "\ndef ",
                "\n\tdef ",
                # Now split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.RST:
            return [
                # Split along section titles
                "\n=+\n",
                "\n-+\n",
                "\n\\*+\n",
                # Split along directive markers
                "\n\n.. *\n\n",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.RUBY:
            return [
                # Split along method definitions
                "\ndef ",
                "\nclass ",
                # Split along control flow statements
                "\nif ",
                "\nunless ",
                "\nwhile ",
                "\nfor ",
                "\ndo ",
                "\nbegin ",
                "\nrescue ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.ELIXIR:
            return [
                # Split along method function and module definition
                "\ndef ",
                "\ndefp ",
                "\ndefmodule ",
                "\ndefprotocol ",
                "\ndefmacro ",
                "\ndefmacrop ",
                # Split along control flow statements
                "\nif ",
                "\nunless ",
                "\nwhile ",
                "\ncase ",
                "\ncond ",
                "\nwith ",
                "\nfor ",
                "\ndo ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.RUST:
            return [
                # Split along function definitions
                "\nfn ",
                "\nconst ",
                "\nlet ",
                # Split along control flow statements
                "\nif ",
                "\nwhile ",
                "\nfor ",
                "\nloop ",
                "\nmatch ",
                "\nconst ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.SCALA:
            return [
                # Split along class definitions
                "\nclass ",
                "\nobject ",
                # Split along method definitions
                "\ndef ",
                "\nval ",
                "\nvar ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nmatch ",
                "\ncase ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.SWIFT:
            return [
                # Split along function definitions
                "\nfunc ",
                # Split along class definitions
                "\nclass ",
                "\nstruct ",
                "\nenum ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\ndo ",
                "\nswitch ",
                "\ncase ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.MARKDOWN:
            return [
                # First, try to split along Markdown headings (starting with level 2)
                "\n#{1,6} ",
                # Note the alternative syntax for headings (below) is not handled here
                # Heading level 2
                # ---------------
                # End of code block
                "```\n",
                # Horizontal lines
                "\n\\*\\*\\*+\n",
                "\n---+\n",
                "\n___+\n",
                # Note that this splitter doesn't handle horizontal lines defined
                # by *three or more* of ***, ---, or ___, but this is not handled
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.LATEX:
            return [
                # First, try to split along Latex sections
                "\n\\\\chapter{",
                "\n\\\\section{",
                "\n\\\\subsection{",
                "\n\\\\subsubsection{",
                # Now split by environments
                "\n\\\\begin{enumerate}",
                "\n\\\\begin{itemize}",
                "\n\\\\begin{description}",
                "\n\\\\begin{list}",
                "\n\\\\begin{quote}",
                "\n\\\\begin{quotation}",
                "\n\\\\begin{verse}",
                "\n\\\\begin{verbatim}",
                # Now split by math environments
                "\n\\\\begin{align}",
                "$$",
                "$",
                # Now split by the normal type of lines
                " ",
                "",
            ]
        if language == Language.HTML:
            return [
                # First, try to split along HTML tags
                "<body",
                "<div",
                "<p",
                "<br",
                "<li",
                "<h1",
                "<h2",
                "<h3",
                "<h4",
                "<h5",
                "<h6",
                "<span",
                "<table",
                "<tr",
                "<td",
                "<th",
                "<ul",
                "<ol",
                "<header",
                "<footer",
                "<nav",
                # Head
                "<head",
                "<style",
                "<script",
                "<meta",
                "<title",
                "",
            ]
        if language == Language.CSHARP:
            return [
                "\ninterface ",
                "\nenum ",
                "\nimplements ",
                "\ndelegate ",
                "\nevent ",
                # Split along class definitions
                "\nclass ",
                "\nabstract ",
                # Split along method definitions
                "\npublic ",
                "\nprotected ",
                "\nprivate ",
                "\nstatic ",
                "\nreturn ",
                # Split along control flow statements
                "\nif ",
                "\ncontinue ",
                "\nfor ",
                "\nforeach ",
                "\nwhile ",
                "\nswitch ",
                "\nbreak ",
                "\ncase ",
                "\nelse ",
                # Split by exceptions
                "\ntry ",
                "\nthrow ",
                "\nfinally ",
                "\ncatch ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.SOL:
            return [
                # Split along compiler information definitions
                "\npragma ",
                "\nusing ",
                # Split along contract definitions
                "\ncontract ",
                "\ninterface ",
                "\nlibrary ",
                # Split along method definitions
                "\nconstructor ",
                "\ntype ",
                "\nfunction ",
                "\nevent ",
                "\nmodifier ",
                "\nerror ",
                "\nstruct ",
                "\nenum ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\ndo while ",
                "\nassembly ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.COBOL:
            return [
                # Split along divisions
                "\nIDENTIFICATION DIVISION.",
                "\nENVIRONMENT DIVISION.",
                "\nDATA DIVISION.",
                "\nPROCEDURE DIVISION.",
                # Split along sections within DATA DIVISION
                "\nWORKING-STORAGE SECTION.",
                "\nLINKAGE SECTION.",
                "\nFILE SECTION.",
                # Split along sections within PROCEDURE DIVISION
                "\nINPUT-OUTPUT SECTION.",
                # Split along paragraphs and common statements
                "\nOPEN ",
                "\nCLOSE ",
                "\nREAD ",
                "\nWRITE ",
                "\nIF ",
                "\nELSE ",
                "\nMOVE ",
                "\nPERFORM ",
                "\nUNTIL ",
                "\nVARYING ",
                "\nACCEPT ",
                "\nDISPLAY ",
                "\nSTOP RUN.",
                # Split by the normal type of lines
                "\n",
                " ",
                "",
            ]
        if language == Language.LUA:
            return [
                # Split along variable and table definitions
                "\nlocal ",
                # Split along function definitions
                "\nfunction ",
                # Split along control flow statements
                "\nif ",
                "\nfor ",
                "\nwhile ",
                "\nrepeat ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.HASKELL:
            return [
                # Split along function definitions
                "\nmain :: ",
                "\nmain = ",
                "\nlet ",
                "\nin ",
                "\ndo ",
                "\nwhere ",
                "\n:: ",
                "\n= ",
                # Split along type declarations
                "\ndata ",
                "\nnewtype ",
                "\ntype ",
                "\n:: ",
                # Split along module declarations
                "\nmodule ",
                # Split along import statements
                "\nimport ",
                "\nqualified ",
                "\nimport qualified ",
                # Split along typeclass declarations
                "\nclass ",
                "\ninstance ",
                # Split along case expressions
                "\ncase ",
                # Split along guards in function definitions
                "\n| ",
                # Split along record field declarations
                "\ndata ",
                "\n= {",
                "\n, ",
                # Split by the normal type of lines
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.POWERSHELL:
            return [
                # Split along function definitions
                "\nfunction ",
                # Split along parameter declarations (escape parentheses)
                "\nparam ",
                # Split along control flow statements
                "\nif ",
                "\nforeach ",
                "\nfor ",
                "\nwhile ",
                "\nswitch ",
                # Split along class definitions (for PowerShell 5.0 and above)
                "\nclass ",
                # Split along try-catch-finally blocks
                "\ntry ",
                "\ncatch ",
                "\nfinally ",
                # Split by normal lines and empty spaces
                "\n\n",
                "\n",
                " ",
                "",
            ]
        if language == Language.VISUALBASIC6:
            vis = r"(?:Public|Private|Friend|Global|Static)\s+"
            return [
                # Split along definitions
                rf"\n(?!End\s){vis}?Sub\s+",
                rf"\n(?!End\s){vis}?Function\s+",
                rf"\n(?!End\s){vis}?Property\s+(?:Get|Let|Set)\s+",
                rf"\n(?!End\s){vis}?Type\s+",
                rf"\n(?!End\s){vis}?Enum\s+",
                # Split along control flow statements
                r"\n(?!End\s)If\s+",
                r"\nElseIf\s+",
                r"\nElse\s+",
                r"\nSelect\s+Case\s+",
                r"\nCase\s+",
                r"\nFor\s+",
                r"\nDo\s+",
                r"\nWhile\s+",
                r"\nWith\s+",
                # Split by the normal type of lines
                r"\n\n",
                r"\n",
                " ",
                "",
            ]

        if language in Language._value2member_map_:
            msg = f"Language {language} is not implemented yet!"
            raise ValueError(msg)
        msg = (
            f"Language {language} is not supported! Please choose from {list(Language)}"
        )
        raise ValueError(msg)


class MarkdownTextSplitter(RecursiveCharacterTextSplitter):
    """Attempts to split the text along Markdown-formatted headings."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a MarkdownTextSplitter."""
        separators = self.get_separators_for_language(Language.MARKDOWN)
        super().__init__(separators=separators, **kwargs)


class MarkdownHeaderTextSplitter:
    """Splitting markdown files based on specified headers."""

    def __init__(
        self,
        headers_to_split_on: list[tuple[str, str]],
        return_each_line: bool = False,  # noqa: FBT001,FBT002
        strip_headers: bool = True,  # noqa: FBT001,FBT002
        custom_header_patterns: dict[str, int] | None = None,
    ) -> None:
        """Create a new MarkdownHeaderTextSplitter.

        Args:
            headers_to_split_on: Headers we want to track
            return_each_line: Return each line w/ associated headers
            strip_headers: Strip split headers from the content of the chunk
            custom_header_patterns: Optional dict mapping header patterns to their
                levels. For example: {"**": 1, "***": 2} to treat **Header** as
                level 1 and ***Header*** as level 2 headers.
        """
        # Output line-by-line or aggregated into chunks w/ common headers
        self.return_each_line = return_each_line
        # Given the headers we want to split on,
        # (e.g., "#, ##, etc") order by length
        self.headers_to_split_on = sorted(
            headers_to_split_on, key=lambda split: len(split[0]), reverse=True
        )
        # Strip headers split headers from the content of the chunk
        self.strip_headers = strip_headers
        # Custom header patterns with their levels
        self.custom_header_patterns = custom_header_patterns or {}

    def _is_custom_header(self, line: str, sep: str) -> bool:
        """Check if line matches a custom header pattern.

        Args:
            line: The line to check
            sep: The separator pattern to match

        Returns:
            True if the line matches the custom pattern format
        """
        if sep not in self.custom_header_patterns:
            return False

        # Escape special regex characters in the separator
        escaped_sep = re.escape(sep)
        # Create regex pattern to match exactly one separator at start and end
        # with content in between
        pattern = (
            f"^{escaped_sep}(?!{escaped_sep})(.+?)(?<!{escaped_sep}){escaped_sep}$"
        )

        match = re.match(pattern, line)
        if match:
            # Extract the content between the patterns
            content = match.group(1).strip()
            # Valid header if there's actual content (not just whitespace or separators)
            # Check that content doesn't consist only of separator characters
            if content and not all(c in sep for c in content.replace(" ", "")):
                return True
        return False

    def aggregate_lines_to_chunks(self, lines: list["LineType"]) -> list[str]:
        """Combine lines with common metadata into chunks.

        Args:
            lines: Line of text / associated header metadata
        """
        aggregated_chunks: list[LineType] = []

        for line in lines:
            if (
                aggregated_chunks
                and aggregated_chunks[-1]["metadata"] == line["metadata"]
            ):
                # If the last line in the aggregated list
                # has the same metadata as the current line,
                # append the current content to the last lines's content
                aggregated_chunks[-1]["content"] += "  \n" + line["content"]
            elif (
                aggregated_chunks
                and aggregated_chunks[-1]["metadata"] != line["metadata"]
                # may be issues if other metadata is present
                and len(aggregated_chunks[-1]["metadata"]) < len(line["metadata"])
                and aggregated_chunks[-1]["content"].split("\n")[-1][0] == "#"
                and not self.strip_headers
            ):
                # If the last line in the aggregated list
                # has different metadata as the current line,
                # and has shallower header level than the current line,
                # and the last line is a header,
                # and we are not stripping headers,
                # append the current content to the last line's content
                aggregated_chunks[-1]["content"] += "  \n" + line["content"]
                # and update the last line's metadata
                aggregated_chunks[-1]["metadata"] = line["metadata"]
            else:
                # Otherwise, append the current line to the aggregated list
                aggregated_chunks.append(line)

        return [
            chunk["content"] for chunk in aggregated_chunks
        ]

    def split_text(self, text: str) -> list[str]:
        """Split markdown file.

        Args:
            text: Markdown file
        """
        # Split the input text by newline character ("\n").
        lines = text.split("\n")
        # Final output
        lines_with_metadata: list[LineType] = []
        # Content and metadata of the chunk currently being processed
        current_content: list[str] = []
        current_metadata: dict[str, str] = {}
        # Keep track of the nested header structure
        header_stack: list[HeaderType] = []
        initial_metadata: dict[str, str] = {}

        in_code_block = False
        opening_fence = ""

        for line in lines:
            stripped_line = line.strip()
            # Remove all non-printable characters from the string, keeping only visible
            # text.
            stripped_line = "".join(filter(str.isprintable, stripped_line))
            if not in_code_block:
                # Exclude inline code spans
                if stripped_line.startswith("```") and stripped_line.count("```") == 1:
                    in_code_block = True
                    opening_fence = "```"
                elif stripped_line.startswith("~~~"):
                    in_code_block = True
                    opening_fence = "~~~"
            elif stripped_line.startswith(opening_fence):
                in_code_block = False
                opening_fence = ""

            if in_code_block:
                current_content.append(stripped_line)
                continue

            # Check each line against each of the header types (e.g., #, ##)
            for sep, name in self.headers_to_split_on:
                is_standard_header = stripped_line.startswith(sep) and (
                    # Header with no text OR header is followed by space
                    # Both are valid conditions that sep is being used a header
                    len(stripped_line) == len(sep) or stripped_line[len(sep)] == " "
                )
                is_custom_header = self._is_custom_header(stripped_line, sep)

                # Check if line matches either standard or custom header pattern
                if is_standard_header or is_custom_header:
                    # Ensure we are tracking the header as metadata
                    if name is not None:
                        # Get the current header level
                        if sep in self.custom_header_patterns:
                            current_header_level = self.custom_header_patterns[sep]
                        else:
                            current_header_level = sep.count("#")

                        # Pop out headers of lower or same level from the stack
                        while (
                            header_stack
                            and header_stack[-1]["level"] >= current_header_level
                        ):
                            # We have encountered a new header
                            # at the same or higher level
                            popped_header = header_stack.pop()
                            # Clear the metadata for the
                            # popped header in initial_metadata
                            if popped_header["name"] in initial_metadata:
                                initial_metadata.pop(popped_header["name"])

                        # Push the current header to the stack
                        # Extract header text based on header type
                        if is_custom_header:
                            # For custom headers like **Header**, extract text
                            # between patterns
                            header_text = stripped_line[len(sep) : -len(sep)].strip()
                        else:
                            # For standard headers like # Header, extract text
                            # after the separator
                            header_text = stripped_line[len(sep) :].strip()

                        header: HeaderType = {
                            "level": current_header_level,
                            "name": name,
                            "data": header_text,
                        }
                        header_stack.append(header)
                        # Update initial_metadata with the current header
                        initial_metadata[name] = header["data"]

                    # Add the previous line to the lines_with_metadata
                    # only if current_content is not empty
                    if current_content:
                        lines_with_metadata.append(
                            {
                                "content": "\n".join(current_content),
                                "metadata": current_metadata.copy(),
                            }
                        )
                        current_content.clear()

                    if not self.strip_headers:
                        current_content.append(stripped_line)

                    break
            else:
                if stripped_line:
                    current_content.append(stripped_line)
                elif current_content:
                    lines_with_metadata.append(
                        {
                            "content": "\n".join(current_content),
                            "metadata": current_metadata.copy(),
                        }
                    )
                    current_content.clear()

            current_metadata = initial_metadata.copy()

        if current_content:
            lines_with_metadata.append(
                {
                    "content": "\n".join(current_content),
                    "metadata": current_metadata,
                }
            )

        # lines_with_metadata has each line with associated header metadata
        # aggregate these into chunks based on common metadata
        if not self.return_each_line:
            return self.aggregate_lines_to_chunks(lines_with_metadata)
        return [
            chunk["content"] for chunk in lines_with_metadata
        ]


class LineType(TypedDict):
    """Line type as typed dict."""

    metadata: dict[str, str]
    content: str


class HeaderType(TypedDict):
    """Header type as typed dict."""

    level: int
    name: str
    data: str


class ExperimentalMarkdownSyntaxTextSplitter:
    """An experimental text splitter for handling Markdown syntax.

    This splitter aims to retain the exact whitespace of the original text while
    extracting structured metadata, such as headers. It is a re-implementation of the
    MarkdownHeaderTextSplitter with notable changes to the approach and
    additional features.

    Key Features:

    * Retains the original whitespace and formatting of the Markdown text.
    * Extracts headers, code blocks, and horizontal rules as metadata.
    * Splits out code blocks and includes the language in the "Code" metadata key.
    * Splits text on horizontal rules (`---`) as well.
    * Defaults to sensible splitting behavior, which can be overridden using the
        `headers_to_split_on` parameter.

    Example:
    ```python
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
    ]
    splitter = ExperimentalMarkdownSyntaxTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    chunks = splitter.split(text)
    for chunk in chunks:
        print(chunk)
    ```

    This class is currently experimental and subject to change based on feedback and
    further development.
    """

    DEFAULT_HEADER_KEYS = {
        "#": "Header 1",
        "##": "Header 2",
        "###": "Header 3",
        "####": "Header 4",
        "#####": "Header 5",
        "######": "Header 6",
    }

    def __init__(
        self,
        headers_to_split_on: list[tuple[str, str]] | None = None,
        return_each_line: bool = False,  # noqa: FBT001,FBT002
        strip_headers: bool = True,  # noqa: FBT001,FBT002
    ) -> None:
        """Initialize the text splitter with header splitting and formatting options.

        This constructor sets up the required configuration for splitting text into
        chunks based on specified headers and formatting preferences.

        Args:
            headers_to_split_on (Union[list[tuple[str, str]], None]):
                A list of tuples, where each tuple contains a header tag (e.g., "h1")
                and its corresponding metadata key. If `None`, default headers are used.
            return_each_line (bool):
                Whether to return each line as an individual chunk.
                Defaults to `False`, which aggregates lines into larger chunks.
            strip_headers (bool):
                Whether to exclude headers from the resulting chunks.
        """
        self.chunks: list[str] = []
        self.current_chunk = ""
        self.current_header_stack: list[tuple[int, str]] = []
        self.strip_headers = strip_headers
        if headers_to_split_on:
            self.splittable_headers = dict(headers_to_split_on)
        else:
            self.splittable_headers = self.DEFAULT_HEADER_KEYS

        self.return_each_line = return_each_line

    def split_text(self, text: str) -> list[str]:
        """Split the input text into structured chunks.

        This method processes the input text line by line, identifying and handling
        specific patterns such as headers, code blocks, and horizontal rules to
        split it into structured chunks based on headers, code blocks, and
        horizontal rules.

        Args:
            text: The input text to be split into chunks.

        Returns:
            A list of `Document` objects representing the structured
            chunks of the input text. If `return_each_line` is enabled, each line
            is returned as a separate `Document`.
        """
        # Reset the state for each new file processed
        self.chunks.clear()
        self.current_chunk = ""
        self.current_header_stack.clear()

        raw_lines = text.splitlines(keepends=True)

        while raw_lines:
            raw_line = raw_lines.pop(0)
            header_match = self._match_header(raw_line)
            code_match = self._match_code(raw_line)
            horz_match = self._match_horz(raw_line)
            if header_match:
                self._complete_chunk_doc()

                if not self.strip_headers:
                    self.current_chunk += raw_line

                # add the header to the stack
                header_depth = len(header_match.group(1))
                header_text = header_match.group(2)
                self._resolve_header_stack(header_depth, header_text)
            elif code_match:
                self._complete_chunk_doc()
                self.current_chunk = self._resolve_code_chunk(
                    raw_line, raw_lines
                )
                self._complete_chunk_doc()
            elif horz_match:
                self._complete_chunk_doc()
            else:
                self.current_chunk += raw_line

        self._complete_chunk_doc()
        # I don't see why `return_each_line` is a necessary feature of this splitter.
        # It's easy enough to do outside of the class and the caller can have more
        # control over it.
        if self.return_each_line:
            return [
                line
                for chunk in self.chunks
                for line in chunk.splitlines()
                if line and not line.isspace()
            ]
        return self.chunks

    def _resolve_header_stack(self, header_depth: int, header_text: str) -> None:
        for i, (depth, _) in enumerate(self.current_header_stack):
            if depth >= header_depth:
                # Truncate everything from this level onward
                self.current_header_stack = self.current_header_stack[:i]
                break
        self.current_header_stack.append((header_depth, header_text))

    def _resolve_code_chunk(self, current_line: str, raw_lines: list[str]) -> str:
        chunk = current_line
        while raw_lines:
            raw_line = raw_lines.pop(0)
            chunk += raw_line
            if self._match_code(raw_line):
                return chunk
        return ""

    def _complete_chunk_doc(self) -> None:
        chunk_content = self.current_chunk
        # Discard any empty documents
        if chunk_content and not chunk_content.isspace():
            # Apply the header stack as metadata
            for depth, value in self.current_header_stack:
                header_key = self.splittable_headers.get("#" * depth)
            self.chunks.append(self.current_chunk)
        # Reset the current chunk
        self.current_chunk = ""

    # Match methods
    def _match_header(self, line: str) -> re.Match[str] | None:
        match = re.match(r"^(#{1,6}) (.*)", line)
        # Only matches on the configured headers
        if match and match.group(1) in self.splittable_headers:
            return match
        return None

    def _match_code(self, line: str) -> re.Match[str] | None:
        matches = [re.match(rule, line) for rule in [r"^```(.*)", r"^~~~(.*)"]]
        return next((match for match in matches if match), None)

    def _match_horz(self, line: str) -> re.Match[str] | None:
        matches = [
            re.match(rule, line) for rule in [r"^\*\*\*+\n", r"^---+\n", r"^___+\n"]
        ]
        return next((match for match in matches if match), None)


class SentenceTransformersTokenTextSplitter(TextSplitter):
    """Splitting text to tokens using sentence model tokenizer."""

    def __init__(
        self,
        chunk_overlap: int = 50,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        tokens_per_chunk: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(**kwargs, chunk_overlap=chunk_overlap)

        if not _HAS_SENTENCE_TRANSFORMERS:
            msg = (
                "Could not import sentence_transformers python package. "
                "This is needed in order to use SentenceTransformersTokenTextSplitter. "
                "Please install it with `pip install sentence-transformers`."
            )
            raise ImportError(msg)

        self.model_name = model_name
        self._model = SentenceTransformer(self.model_name)
        self.tokenizer = self._model.tokenizer
        self._initialize_chunk_configuration(tokens_per_chunk=tokens_per_chunk)

    def _initialize_chunk_configuration(self, *, tokens_per_chunk: int | None) -> None:
        self.maximum_tokens_per_chunk = self._model.max_seq_length

        if tokens_per_chunk is None:
            self.tokens_per_chunk = self.maximum_tokens_per_chunk
        else:
            self.tokens_per_chunk = tokens_per_chunk

        if self.tokens_per_chunk > self.maximum_tokens_per_chunk:
            msg = (
                f"The token limit of the models '{self.model_name}'"
                f" is: {self.maximum_tokens_per_chunk}."
                f" Argument tokens_per_chunk={self.tokens_per_chunk}"
                f" > maximum token limit."
            )
            raise ValueError(msg)

    def split_text(self, text: str) -> list[str]:
        """Splits the input text into smaller components by splitting text on tokens.

        This method encodes the input text using a private `_encode` method, then
        strips the start and stop token IDs from the encoded result. It returns the
        processed segments as a list of strings.

        Args:
            text: The input text to be split.

        Returns:
            A list of string components derived from the input text after encoding and
            processing.
        """

        def encode_strip_start_and_stop_token_ids(text: str) -> list[int]:
            return self._encode(text)[1:-1]

        tokenizer = Tokenizer(
            chunk_overlap=self._chunk_overlap,
            tokens_per_chunk=self.tokens_per_chunk,
            decode=self.tokenizer.decode,
            encode=encode_strip_start_and_stop_token_ids,
        )

        return split_text_on_tokens(text=text, tokenizer=tokenizer)

    def count_tokens(self, *, text: str) -> int:
        """Counts the number of tokens in the given text.

        This method encodes the input text using a private `_encode` method and
        calculates the total number of tokens in the encoded result.

        Args:
            text: The input text for which the token count is calculated.

        Returns:
            int: The number of tokens in the encoded text.
        """
        return len(self._encode(text))

    _max_length_equal_32_bit_integer: int = 2**32

    def _encode(self, text: str) -> list[int]:
        token_ids_with_start_and_end_token_ids = self.tokenizer.encode(
            text,
            max_length=self._max_length_equal_32_bit_integer,
            truncation="do_not_truncate",
        )
        return cast("list[int]", token_ids_with_start_and_end_token_ids)




if __name__ == '__main__':
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("/Users/cuils/lscui/study/models/BAAI/bge-m3")

    text_splitter = MarkdownTextSplitter.from_huggingface_tokenizer(
        tokenizer=tokenizer,
        chunk_overlap=64,
        chunk_size=tokenizer.model_max_length,
    )

    with open("../../temp/temp1.md", encoding="utf-8") as f:
        text = f.read()

    res = text_splitter.split_text(text)
    import time
    for chunk in res:
        print("#######"*10)
        print(chunk.strip())
        exit()

