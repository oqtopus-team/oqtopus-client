(function () {
  "use strict";

  function renameFunctionsToMethods(root) {
    root.querySelectorAll("h3").forEach((heading) => {
      const text = heading.textContent ? heading.textContent.trim() : "";
      if (text.startsWith("Functions")) {
        heading.childNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            node.textContent = node.textContent.replace("Functions", "Methods");
          }
        });
      }
    });

    root.querySelectorAll(".md-nav__title, .md-nav__link").forEach((el) => {
      if (el.textContent && el.textContent.includes("Functions")) {
        el.textContent = el.textContent.replace(/Functions/g, "Methods");
      }
    });

    root.querySelectorAll("nav[aria-label='Functions']").forEach((nav) => {
      nav.setAttribute("aria-label", "Methods");
    });
  }

  function moveMethodsBeforeAttributes(root) {
    root.querySelectorAll(".doc.doc-children").forEach((container) => {
      const headings = Array.from(container.children).filter(
        (el) => el.tagName === "H3",
      );

      const attrHeading = headings.find((h) =>
        (h.textContent || "").trim().startsWith("Attributes"),
      );
      const fnHeading = headings.find((h) =>
        (h.textContent || "").trim().startsWith("Functions"),
      );

      if (!attrHeading || !fnHeading) {
        return;
      }

      const methodBlock = [fnHeading];
      let cursor = fnHeading.nextElementSibling;
      while (cursor && cursor.tagName !== "H3") {
        methodBlock.push(cursor);
        cursor = cursor.nextElementSibling;
      }

      methodBlock.forEach((el) => container.insertBefore(el, attrHeading));
    });
  }

  function moveMethodsBeforeAttributesInToc(root) {
    root.querySelectorAll("a.md-nav__link[href$='-attributes']").forEach((attrLink) => {
      const attrHref = attrLink.getAttribute("href");
      if (!attrHref) {
        return;
      }

      const methodsHref = attrHref.replace(/-attributes$/, "-functions");
      const list = attrLink.closest("ul, ol");
      if (!list) {
        return;
      }

      const methodsLink = Array.from(list.querySelectorAll("a.md-nav__link")).find(
        (link) => link.getAttribute("href") === methodsHref,
      );
      if (!methodsLink) {
        return;
      }

      const attrItem = attrLink.closest("li");
      const methodsItem = methodsLink.closest("li");
      if (!attrItem || !methodsItem || attrItem.parentElement !== methodsItem.parentElement) {
        return;
      }

      attrItem.parentElement.insertBefore(methodsItem, attrItem);
    });
  }

  function patchApiReference() {
    const root = document;
    moveMethodsBeforeAttributes(root);
    moveMethodsBeforeAttributesInToc(root);
    renameFunctionsToMethods(root);
  }

  if (typeof window.document$ !== "undefined") {
    window.document$.subscribe(patchApiReference);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", patchApiReference);
  } else {
    patchApiReference();
  }
})();
