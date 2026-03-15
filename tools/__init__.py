from tools.bash_tool import bash
from tools.file_read_tool import file_read
from tools.file_edit_tool import file_edit, file_write
from tools.glob_tool import glob_search
from tools.grep_tool import grep_search
from tools.patch_tool import apply_patch_tool
from tools.test_tool import run_tests
from rag.rag_tool import rag_retrieve


def get_all_tools():
    return [
        bash,
        file_read,
        file_edit,
        file_write,
        glob_search,
        grep_search,
        apply_patch_tool,
        run_tests,
        rag_retrieve,
    ]
