-- Keep Markdown and the website unchanged; indent the PDF's heading tree.

-- A list whose items start with a `[date]{.cvdate}` span is a list of dated rows
-- (the one-page CV): lay it out as a date column and a text column.
local function dated_rows(list)
  local rows = {}
  for _, item in ipairs(list.content) do
    local first = item[1]
    if not first or (first.t ~= "Plain" and first.t ~= "Para") then return nil end
    local inlines = first.content
    local span = inlines[1]
    if not span or span.t ~= "Span" or not span.classes:includes("cvdate") then return nil end
    local rest = pandoc.List()
    for i = 2, #inlines do rest:insert(inlines[i]) end
    while #rest > 0 and (rest[1].t == "Space" or rest[1].t == "SoftBreak") do rest:remove(1) end
    local date = pandoc.write(pandoc.Pandoc({pandoc.Plain(span.content)}), "latex")
    local text = pandoc.write(pandoc.Pandoc({pandoc.Plain(rest)}), "latex")
    rows[#rows + 1] = date .. " & " .. text .. " \\\\"
  end
  if #rows == 0 then return nil end
  return pandoc.RawBlock("latex", "\\begin{cvdated}\n" .. table.concat(rows, "\n") .. "\n\\end{cvdated}")
end

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
    elseif block.t == "BulletList" and dated_rows(block) then
      blocks:insert(dated_rows(block))
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
