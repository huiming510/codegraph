# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/13 16:58
# @Author  : cuils
# @Description:
"""
import os
import subprocess
from pathlib import Path
from subprocess import SubprocessError
from .base_converter import BaseFormatConverter


class PandocFormatConverter(BaseFormatConverter):
    def __init__(self, engine_path=None, cache_dir=None):
        super().__init__(cache_dir)
        self.engine_path = engine_path
        try:
            cmd = [self.engine_path or "pandoc", "--version"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        except:
            raise FileNotFoundError("Pandoc engine not found")

    @property
    def list_input_formats(self):
        return {"asciidoc", "biblatex", "bibtex", "bits", "commonmark", "commonmark_x", "creole", "csljson", "csv",
                "djot", "docbook", "docx", "dokuwiki", "endnotexml", "epub", "fb2", "gfm", "haddock", "html", "ipynb",
                "jats", "jira", "json", "latex", "man", "markdown", "markdown_github", "markdown_mmd",
                "markdown_phpextra", "markdown_strict", "mdoc", "mediawiki", "muse", "native", "odt", "opml", "org",
                "pod", "pptx", "ris", "rst", "rtf", "t2t", "textile", "tikiwiki", "tsv", "twiki", "typst", "vimwiki",
                "xlsx", "xml"}

    @property
    def list_output_formats(self):
        return {"ansi", "asciidoc", "asciidoc_legacy", "asciidoctor", "bbcode", "bbcode_fluxbb", "bbcode_hubzilla",
                "bbcode_phpbb", "bbcode_steam", "bbcode_xenforo", "beamer", "biblatex", "bibtex", "chunkedhtml",
                "commonmark", "commonmark_x", "context", "csljson", "djot", "docbook", "docbook4", "docbook5", "docx",
                "dokuwiki", "dzslides", "epub", "epub2", "epub3", "fb2", "gfm", "haddock", "html", "html4", "html5",
                "icml", "ipynb", "jats", "jats_archiving", "jats_articleauthoring", "jats_publishing", "jira", "json",
                "latex", "man", "markdown", "markdown_github", "markdown_mmd", "markdown_phpextra", "markdown_strict",
                "markua", "mediawiki", "ms", "muse", "native", "odt", "opendocument", "opml", "org", "pdf", "plain",
                "pptx", "revealjs", "rst", "rtf", "s5", "slideous", "slidy", "tei", "texinfo", "textile", "typst",
                "vimdoc", "xml", "xwiki", "zimwiki"}

    def convert(self, input_filepath, input_format, output_format, output_suffix):
        """输入文件地址，输出转换后的文件地址
        params:
        input_filepath: 原始文件地址
        input_format: 原始文件格式
        output_format: 目标转换格式
        output_suffix: 转换后文件后缀，格式和后缀会存在差异，docx格式和后缀完全一样，markdown后缀为md
        """
        input_filepath = Path(input_filepath)
        output_filepath = os.path.join(self.cache_dir, f"{input_filepath.stem}.{output_suffix.lstrip('.')}")
        media_path = os.path.join(self.cache_dir, f"media-{input_filepath.stem}")
        # 格式作为参数传入时，不能加.，此处额外处理一下，防止传错。例：docx 和 .docx
        input_format = input_format.lstrip(".")
        output_format = output_format.lstrip(".")
        if input_format not in self.list_input_formats:
            raise ValueError(f"Pandoc input format `{input_format}` is not supported. only {self.list_input_formats}")
        if output_format not in self.list_output_formats:
            raise ValueError(f"Pandoc output format `{output_format}` is not supported. only {self.list_output_formats}")

        cmd = [
            self.engine_path or "pandoc",
            "-f", input_format,
            "-t", output_format,
            "--track-changes=all",
            "--standalone", # 保留分节页码
            "--wrap=none", # 不硬换行
            "--extract-media", media_path,
            input_filepath,
            "-o", output_filepath
        ]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)

        if p.returncode == 0 and os.path.exists(output_filepath):
            return output_filepath, os.path.join(media_path, "media")
        else:
            raise SubprocessError(p.stderr)


if __name__ == '__main__':
    converter = PandocFormatConverter()