function removeAttributesExceptSrcHrefAlt(element) {
  const attributes = element.attributes;
  for (let i = attributes.length - 1; i >= 0; i--) {
    const attrName = attributes[i].name;
    if (attrName !== 'src' && attrName !== 'href' && attrName !== 'alt' && attrName !== 'img') {
      element.removeAttribute(attrName);
    }
  }
  element.removeAttribute("class")
  element.removeAttribute("srcset")
  element.removeAttribute("style")
  element.removeAttribute("sizes")
}

function minify_html(input) {
  return input
    .replace(/\<\!--\s*?[^\s?\[][\s\S]*?--\>/g, '')
    .replace(/\>\s*\</g, '><')
    .replace(/\s\s+/g, '')
}

// Function to traverse and process all elements in the document
function processAllElements(query) {
  const target = document.querySelector(query);
  const allElements = target.querySelectorAll('*');

  const tagsToRemove = ["script", "svg", "style", "iframe", "input"];

  tagsToRemove.forEach(tag => {
    target.querySelectorAll(tag).forEach(el => {
      el.remove()
    })
  });

  allElements.forEach(function (element) {
    const bg = window.getComputedStyle(element).getPropertyValue("background-image");
    if (bg.startsWith("url")) {
      element.setAttribute("img", bg.split('"')[1])
      console.log(element)
    }
    removeAttributesExceptSrcHrefAlt(element);
  });

  if (document.querySelector(query)) {
    return minify_html(target.outerHTML);
  }
}

return processAllElements("|*SELECTOR*|");