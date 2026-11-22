-- Keep Markdown and the website unchanged; indent the PDF's heading tree.
function Pandoc(doc)
  if not FORMAT:match("latex") then
    return doc
  end

  local blocks = pandoc.List()
  local levels = {}

  local function close_to(level)
    while #levels > 0 and levels[#levels] >= level do
      blocks:insert(pandoc.RawBlock("latex", "\\end{cvindent}"))
      table.remove(levels)
    end
  end

  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" then
      close_to(block.level)
      blocks:insert(block)
      blocks:insert(pandoc.RawBlock("latex", "\\begin{cvindent}"))
      levels[#levels + 1] = block.level
    elseif block.t == "HorizontalRule" then
      -- Section separators belong to the page margin, not the last subsection.
      close_to(0)
      blocks:insert(block)
    elseif block.t == "BulletList" and #levels > 0 and levels[#levels] <= 2 then
      -- A list straight under a section title (no `###` group) steps in once more,
      -- so every section shows the same staircase.
      blocks:insert(pandoc.RawBlock("latex", "\\begin{cvindent}"))
      blocks:insert(block)
      blocks:insert(pandoc.RawBlock("latex", "\\end{cvindent}"))
    else
      blocks:insert(block)
    end
  end

  close_to(0)
  doc.blocks = blocks
  return doc
end
