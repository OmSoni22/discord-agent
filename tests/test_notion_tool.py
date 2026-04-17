from unittest.mock import MagicMock
from app.tools.notion_tool import NotionTool

def test_replace_content():
    tool = NotionTool()
    mock_client = MagicMock()
    mock_client.blocks.children.list.return_value = {
        "results": [{"id": "block-1"}, {"id": "block-2"}]
    }

    result = tool._replace_content(mock_client, "page-id-123", "New Content!")

    assert "successfully replaced" in result
    mock_client.blocks.children.list.assert_called_once_with(block_id="page-id-123")
    assert mock_client.blocks.delete.call_count == 2
    mock_client.blocks.children.append.assert_called_once()
    
def test_update_block():
    tool = NotionTool()
    mock_client = MagicMock()

    result = tool._update_block(mock_client, "block-123", "Updated test content")
    
    assert "updated successfully" in result
    mock_client.blocks.update.assert_called_once()

def test_update_properties():
    tool = NotionTool()
    mock_client = MagicMock()

    result = tool._update_properties(mock_client, "page-123", "New Page Title")
    
    assert "properties updated successfully" in result
    mock_client.pages.update.assert_called_once()
