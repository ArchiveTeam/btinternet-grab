-- A simple download counter for Wget.
url_count = 0

wget.callbacks.get_urls = function(file, url, is_css, iri)
  -- progress message
  url_count = url_count + 1
  if url_count % 50 == 0 then
    print(" - Downloaded "..url_count.." URLs")
  end

  return {}
end

