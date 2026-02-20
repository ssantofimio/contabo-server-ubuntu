/** @odoo-module **/

import { Component, useRef, onMounted, onWillStart, onPatched, onWillUnmount, useState, markup } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";
import { Chatter } from "@mail/core/web/chatter";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { usePopover } from "@web/core/popover/popover_hook";

export class KnowledgeSplit extends Component {
    static template = "i8_knowledge_management.KnowledgeSplit";
    static components = { Chatter };
    static tRefs = true;

    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        this.title = useService("title");

        // Parche robusto: Interceptamos cualquier cambio al título para forzar nuestra lógica
        this._originalSetParts = this.title.setParts.bind(this.title);
        this.title.setParts = (parts) => {
            const newParts = { ...parts, zopenerp: null }; // Siempre quitar Odoo
            const currentName = (this.state && this.state.currentArticleName) || localStorage.getItem("last_article_name");
            if (newParts.action && currentName) {
                newParts.action = currentName;
            }
            this._originalSetParts(newParts);
        };

        // Título inicial inmediato para evitar parpadeo
        const lastTitle = localStorage.getItem("last_article_name") || _t("Espacio de Trabajo");
        this.title.setParts({ zopenerp: null, action: lastTitle });

        this.popover = usePopover(EmojiPicker);

        this.onWysiwygStarted = async (wysiwygInstance) => {
            this.wysiwyg = wysiwygInstance;
            try {
                await this.wysiwyg.startEdition();

                // Monitor changes for auto-save (significant content changes only)
                const onContentChange = () => {
                    if (!this.wysiwyg || !this.state.currentArticle) return;
                    const newContent = this.wysiwyg.getValue();
                    if (newContent !== this._lastSavedContent) {
                        this.state.saveStatus = 'dirty';
                        this.debouncedSave();
                    }
                };

                this.wysiwyg.el.addEventListener('input', onContentChange);
                this.wysiwyg.el.addEventListener('keyup', (e) => {
                    // Only trigger on keys that actually change content
                    const significantKeys = ['Enter', 'Backspace', 'Delete'];
                    if (significantKeys.includes(e.key)) onContentChange();
                });

                // MutationObserver captures DOM changes (media insertion, etc.)
                // We exclude attributes to avoid saving on selection/focus changes
                if (this.contentObserver) this.contentObserver.disconnect();
                this.contentObserver = new MutationObserver(onContentChange);
                this.contentObserver.observe(this.wysiwyg.el, {
                    childList: true,
                    subtree: true,
                    characterData: true,
                    attributes: false
                });

                // Focus the editor immediately
                this.wysiwyg.focus();

            } catch (err) {
            }
        };

        this.debouncedSave = useDebounced(this.saveArticle.bind(this), 1500); // More aggressive auto-save

        this.root = useRef("root-template");
        this.splitter = useRef("splitter");
        this.cardPanel = useRef("cardPanel");
        this.cardToggleIcon = useRef("cardToggleIcon");

        this.debouncedSearch = useDebounced(this._performSearch.bind(this), 300);

        this.articles = [];
        this.filteredArticles = [];
        this.searching = false;
        this.tagMatchedIds = new Set();
        this.viewedArticles = new Set(
            JSON.parse(sessionStorage.getItem("viewedArticles") || "[]")
        );
        this.partnerIdPromise = this._getPartnerId();
        this.userCache = new Map();
        this.articleContentCache = new Map();

        this.state = useState({
            isFollowing: false,
            commentLoading: false,
            currentArticleName: null,
            showSearchPanel: false,
            searchResults: [],
            onlyFavorites: false,
            favoriteMap: {},
            showMoreOptions: false,
            showMetadata: false,
            createdBy: '',
            createdByAvatar: '',
            createdOn: '',
            modifiedBy: '',
            modifiedByAvatar: '',
            modifiedOn: '',
            selectedTags: [],
            availableTags: [],
            showDropdown: false,
            showRenameModal: false,
            renameTitle: '',
            showMoveModal: false,
            moveTargetId: null,
            selectedMoveTarget: null,
            breadcrumbHtml: '',
            isLoading: true, // Silent load
            collapsedNodes: new Set(),
            showArchived: false,
            showArchiveModal: false,
            showUnarchiveModal: false,
            showSharePanel: false, // Share Popover State
            recursivePublish: true, // Default to recursive
            canArchive: false,
            canUnarchive: false,
            isActive: true,
            showNewArticlePanel: false,
            newArticleTitle: "",
            creatingArticle: false,
            showCopyModal: false,
            copyTitle: '',
            showTagModal: false,
            selectedTagIds: [],
            tagSearch: '',
            versionHistory: [],
            showVersionHistoryPanel: false,
            historyTab: 'content',
            selectedVersionId: null,
            selectedVersionContent: '',
            selectedVersionMetadata: null,
            showDiffPanel: false,
            diffHtml: '',
            oldVersionId: null,
            currentVersionId: null,
            compareSourceVersionId: null,
            compareTargetVersionId: null,
            viewsCount: 0,
            likesCount: 0,
            likedByIds: [],
            sortOrder: "name",
            searchInContent: localStorage.getItem("search_in_content") === "1",
            sidebarCollapsed: false,
            articleHistory: [],
            historyIndex: -1,
            saveStatus: 'saved', // 'saved', 'dirty', 'saving'
            isEditing: true, // Siempre en modo edición
            showChatter: false,
            currentArticleContent: "",
            currentArticle: null,
            showCardPanel: false,
            // Cover Image State
            showCoverModal: false,
            isRepositioning: false,
            coverModalTab: 'gallery', // gallery, upload, url
            coverImageURLInput: '',
        });

        // Bind methods to ensure 'this' is correct in templates
        this.openCoverModal = this.openCoverModal.bind(this);
        this.closeCoverModal = this.closeCoverModal.bind(this);
        this.updateCover = this.updateCover.bind(this);
        this.onCoverUpload = this.onCoverUpload.bind(this);
        this.addCover = this.addCover.bind(this);
        this.removeCover = this.removeCover.bind(this);
        this.toggleReposition = this.toggleReposition.bind(this);
        this.saveCoverPosition = this.saveCoverPosition.bind(this);
        this.openIconPicker = this.openIconPicker.bind(this);
        this.cancelReposition = this.cancelReposition.bind(this);
        this.onGlobalClick = this.onGlobalClick.bind(this);
        this.openRenameModal = this.openRenameModal.bind(this);
        this.cancelRename = this.cancelRename.bind(this);
        this.confirmRename = this.confirmRename.bind(this);

        onMounted(() => {
            document.addEventListener("click", this.onGlobalClick, true);
            this._onMounted();
        });
        onWillUnmount(() => {
            document.removeEventListener("click", this.onGlobalClick, true);
            // Restaurar el servicio de título al salir
            if (this._originalSetParts) {
                this.title.setParts = this._originalSetParts;
                this.title.setParts({ zopenerp: "Odoo" });
            }
        });
        onPatched(() => {
            if (this.root.el) {
                this._refreshTree(this.isFilteredView);
            }
        });
        onWillStart(async () => {
            await loadBundle("web_editor.backend_assets_wysiwyg");
            const wysiwygModule = await odoo.loader.modules.get("@web_editor/js/wysiwyg/wysiwyg");
            this.Wysiwyg = wysiwygModule.Wysiwyg;
        });
    }

    get wysiwygProps() {
        return {
            options: {
                value: this.state.currentArticleContent,
                recordInfo: {
                    res_id: this.state.currentArticle?.id,
                    res_model: 'knowledge.article',
                },
                noAttachment: true,
            },
            startWysiwyg: this.onWysiwygStarted,
        };
    }

    get articleContentMarkup() {
        return markup(this.state.currentArticleContent || "");
    }

    get breadcrumbs() {
        if (!this.state.currentArticle) return [];

        const fullPath = [];
        let current = this.state.currentArticle;

        // Traverse upwards including current
        fullPath.unshift(current);
        while (current && current.parent_id) {
            const parentId = Array.isArray(current.parent_id) ? current.parent_id[0] : current.parent_id;
            const parent = this.articles.find(a => a.id === parentId);
            if (parent) {
                fullPath.unshift(parent);
                current = parent;
            } else {
                break;
            }
        }

        // Truncation Logic: If depth > 3, show [Root, Ellipsis, LastParent, Current]
        if (fullPath.length > 3) {
            const hidden = fullPath.slice(1, fullPath.length - 2);
            return [
                { type: 'article', data: fullPath[0] },
                { type: 'ellipsis', items: hidden, title: hidden.map(h => h.name).join(' > ') },
                { type: 'article', data: fullPath[fullPath.length - 2] },
                { type: 'article', data: fullPath[fullPath.length - 1] }
            ];
        }

        return fullPath.map(p => ({ type: 'article', data: p }));
    }

    _onBreadcrumbClick(articleId) {
        this.renderArticle(this.articles.find(a => a.id === articleId));
    }



    async _onMounted() {
        this._restorePersistedState();
        this._initStickyToolbar();

        // Initialize tags and articles
        await this.loadArticles();

        // 1. Try context from props (Immediate Action Context)
        let initialId = this.props.action?.context?.article_id || this.props.action?.params?.article_id;

        // 2. Fallback to URL Hash (Robust Extraction)
        if (!initialId) {
            const match = window.location.hash.match(/article_id=(\d+)/);
            if (match) {
                initialId = parseInt(match[1]);
            }
        }

        // 3. Fallback to Last Selected
        if (!initialId && this.lastSelectedArticleId) {
            initialId = this.lastSelectedArticleId;
        }

        let initialArticle = null;
        if (initialId) {
            initialArticle = this.allArticles.find(a => a.id === parseInt(initialId));
        }

        this.filterArticles();
        this.renderArticle(initialArticle || this.articles[0]);

        this._initSplitter();
        this._bindUI();

        this._boundGlobalClick = this._onGlobalClick.bind(this);
        this._boundEscape = this._onEscapeKey.bind(this);
        this._boundBreadcrumb = this.handleBreadcrumbClick.bind(this);

        document.addEventListener("click", this._boundGlobalClick, { passive: true });
        document.addEventListener("keydown", this._boundEscape);
        document.addEventListener("click", this._boundBreadcrumb, { passive: true });

        this._boundCleanup = () => {
            document.removeEventListener("click", this._boundGlobalClick);
            document.removeEventListener("keydown", this._boundEscape);
            document.removeEventListener("click", this._boundBreadcrumb);
            window.removeEventListener("beforeunload", this._boundCleanup);
        };
        window.addEventListener("beforeunload", this._boundCleanup, { once: true });

        this._newArticleAutoFocus();
        this._saveOnEnter();
        this.root.el.querySelectorAll(".o_article_list").forEach(el => {
            el.addEventListener("click", this._onTreeToggleClick.bind(this));
        });

        const rootEl = this.root.el;
        if (this.state.sidebarCollapsed) {
            rootEl.classList.add("sidebar-collapsed");
        } else {
            rootEl.classList.remove("sidebar-collapsed");
        }

        const sidebar = this.root.el.querySelector(".o_knowledge_sidebar");
        const savedWidth = parseInt(localStorage.getItem("sidebar_width"), 10);
        if (!isNaN(savedWidth) && savedWidth >= 150 && savedWidth <= 600) {
            sidebar.style.width = savedWidth + "px";
        }
        this.state.isLoading = false;
    }

    async loadArticles() {
        const partnerId = await this.partnerIdPromise;

        const [allRecords] = await Promise.all([
            this.orm.searchRead("knowledge.article",
                ["|", ["is_published", "=", true], ["author_id", "=", this.user.userId]],
                [
                    "id", "name", "parent_id", "tag_ids", "active", "display_name",
                    "views_count", "likes_count", "liked_by_ids",
                    "create_date", "write_date", "create_uid", "write_uid", "share_token",
                    "author_id", "is_published",
                    "cover_image_type", "cover_image_url", "cover_image_binary", "cover_position",
                    "favorite_user_ids", "icon"
                ],
                { context: { active_test: false } }
            ),
        ]);

        const favMap = {};
        for (const r of allRecords) {
            if (r.favorite_user_ids && r.favorite_user_ids.includes(this.user.userId)) {
                favMap[r.id] = true;
            }
        }
        this.state.favoriteMap = favMap;

        const tagName = (id) => this.tagIdToName?.get(id) || "";

        const enriched = allRecords.map(r => ({
            ...r,
            parent_id: r.parent_id ? r.parent_id[0] : null,
            tag_ids_raw: r.tag_ids,
            tag_ids: (r.tag_ids || []).map(tagName),
            expanded: true,
        }));

        this.allArticles = enriched;
        this.articles = enriched;


        if (this.state.onlyFavorites || this.state.selectedTags.length) {
            for (const article of this.filteredArticles) {
                let parentId = article.parent_id;
                while (parentId) {
                    const parent = this.articles.find(a => a.id === parentId);
                    if (parent) {
                        parent.expanded = true;
                        parentId = parent.parent_id;
                    } else break;
                }
            }
        }
    }

    _refreshTree(isFiltered = false) {
        const source = isFiltered ? this.filteredArticles : this.articles;

        const listFav = this.root.el.querySelector(".o_article_list_favorites");
        const listWork = this.root.el.querySelector(".o_article_list_workspace");
        const listPriv = this.root.el.querySelector(".o_article_list_private");

        [listFav, listWork, listPriv].forEach(l => l ? l.innerHTML = "" : null);

        if (!source.length) {
            if (listWork) {
                const noMatch = document.createElement("div");
                noMatch.className = "text-muted small px-3 py-2 d-flex align-items-center";
                noMatch.innerHTML = `<i class="fa fa-folder-open me-2"></i> No se encontraron artículos.`;
                listWork.appendChild(noMatch);
            }
            return;
        }

        // Split articles into categories
        const currentUserId = this.user.userId;
        const favs = source.filter(a => this.state.favoriteMap[a.id]);
        const workspace = source.filter(a => {
            const isAuthor = a.author_id && a.author_id[0] === currentUserId;
            return !isAuthor || a.is_published;
        });
        const privates = source.filter(a => {
            const isAuthor = a.author_id && a.author_id[0] === currentUserId;
            return isAuthor && !a.is_published;
        });

        if (listFav) this._renderTree(listFav, favs, "favorites_root");
        if (listWork) this._renderTree(listWork, workspace);
        if (listPriv) this._renderTree(listPriv, privates);

        // Hide empty sections (Updated class for Enterprise)
        [listFav, listWork, listPriv].forEach(l => {
            if (l) {
                const section = l.closest(".o_knowledge_section_ent");
                if (section) {
                    const hasChildren = !!l.children.length;
                    section.classList.toggle("d-none", !hasChildren);
                }
            }
        });
    }

    _renderTree(container, articles, parentId = null) {
        let children;
        let isFavoritesRoot = false;

        if (parentId === "favorites_root") {
            children = articles; // The provided list IS the list of roots to render
            isFavoritesRoot = true;
            parentId = null;
        } else if (parentId === "flat") {
            children = articles;
            parentId = null;
        } else {
            // Normal recursive case: find children of parentId in the full/filtered set
            children = articles.filter(a => a.parent_id === parentId);
        }

        if (!children.length) return;

        // Use the container directly if it's the root UL, otherwise create a nested UL
        let targetUl;
        if (parentId === null) {
            targetUl = container;
            targetUl.innerHTML = ""; // Clear existing before rendering
        } else {
            targetUl = document.createElement("ul");
            targetUl.classList.add("o_tree");
            container.appendChild(targetUl);
        }

        const q = (this.state.query || "").toLowerCase();

        for (const article of children) {
            // Check for children in the FULL set of articles (or filtered set if applicable), 
            // NOT just within the subset passed to this function.
            // If we are in favorites root, we look at the global source to find children.
            const sourceForChildren = this.isFilteredView ? this.filteredArticles : this.articles;
            const hasChildren = sourceForChildren.some(a => a.parent_id === article.id);

            const li = document.createElement("li");
            li.dataset.articleId = article.id;
            li.classList.add("o_article", "position-relative");
            if (hasChildren) {
                li.classList.add("o_article_has_children");
            }

            const handle = document.createElement("div");
            handle.classList.add("o_article_handle", "d-flex", "align-items-center");
            if (this.state.currentArticle?.id === article.id) {
                handle.classList.add("o_article_active");
            }

            // Caret (Collapse/Expand)
            const caret = document.createElement("a");
            caret.classList.add("o_article_caret", "btn", "btn-link", "text-muted", "p-0");
            caret.setAttribute("role", "button");
            const caretIcon = document.createElement("i");
            caretIcon.classList.add("align-self-center", "fa", "fa-fw");
            caretIcon.classList.add(article.expanded ? "fa-caret-down" : "fa-caret-right");
            caret.appendChild(caretIcon);

            if (hasChildren) {
                caret.addEventListener("click", (e) => {
                    e.stopPropagation();
                    article.expanded = !article.expanded;
                    localStorage.setItem("expanded_nodes", JSON.stringify(
                        this.articles.filter(a => a.expanded).map(a => a.id)
                    ));
                    this._refreshTree(this.isFilteredView);
                });
            } else {
                caret.style.visibility = "hidden";
            }
            handle.appendChild(caret);

            const contentWrapper = document.createElement("div");
            contentWrapper.classList.add("w-100", "d-flex", "min-w-0", "align-items-center");

            // Emoji/Icon
            const emoji = document.createElement("a");
            emoji.classList.add("o_article_emoji", "p-1");
            emoji.setAttribute("role", "button");
            emoji.innerText = article.icon || (hasChildren ? "📁" : "📄");

            // Allow changing icon by clicking it
            emoji.addEventListener("click", (e) => {
                e.stopPropagation();
                // We need to set this article as current if we want to change its icon, 
                // or we can just pass the target article to openIconPicker.
                // For now, let's assume it only works if it's the current article or we auto-select it.
                if (this.state.currentArticleId !== article.id) {
                    this.renderArticle(article).then(() => {
                        this.openIconPicker(e);
                    });
                } else {
                    this.openIconPicker(e);
                }
            });

            contentWrapper.appendChild(emoji);

            // Name/Label
            const name = document.createElement("a");
            name.classList.add("o_article_name", "p-1", "flex-grow-1", "text-truncate");
            name.setAttribute("role", "button");
            if (this.state.currentArticle?.id === article.id) {
                name.classList.add("fw-bold", "text-900");
            } else {
                name.classList.add("text-muted");
            }

            const idx = article.name.toLowerCase().indexOf(q);
            if (q && idx !== -1) {
                const before = article.name.slice(0, idx);
                const match = article.name.slice(idx, idx + q.length);
                const after = article.name.slice(idx + q.length);
                name.innerHTML = `${before}<mark>${match}</mark>${after}`;
            } else {
                name.textContent = article.name;
            }

            name.addEventListener("click", (e) => {
                e.stopPropagation();
                this.renderArticle(article);
            });
            contentWrapper.appendChild(name);

            // Create Child Button
            const createBtn = document.createElement("a");
            createBtn.classList.add("o_article_create", "p-1");
            createBtn.setAttribute("role", "button");
            createBtn.innerHTML = '<i class="fa fa-fw fa-plus" title="Crear un artículo anidado"></i>';
            createBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                this.createQuickArticleInSection(article.is_published, article.id);
            });
            contentWrapper.appendChild(createBtn);

            handle.appendChild(contentWrapper);
            li.appendChild(handle);

            if (q && article.content) {
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = article.content;
                const contentText = tempDiv.textContent || "";

                const index = contentText.toLowerCase().indexOf(q);
                if (index !== -1) {
                    const snippet = contentText.substring(Math.max(index - 20, 0), index + q.length + 20);
                    const preview = document.createElement("div");
                    preview.classList.add("tree-snippet");

                    const before = snippet.slice(0, index);
                    const match = snippet.slice(index, index + q.length);
                    const after = snippet.slice(index + q.length);

                    preview.innerHTML = `... ${before}<mark>${match}</mark>${after} ...`;
                    li.appendChild(preview);
                }
            }

            if (hasChildren) {
                // Determine which source to use for recursion
                // If we are in favorites root, we switch to normal recursion using the global source
                const nextSource = isFavoritesRoot ? (this.isFilteredView ? this.filteredArticles : this.articles) : articles;

                // If expanded, render children properly
                if (article.expanded) {
                    this._renderTree(li, nextSource, article.id);
                }
            }

            targetUl.appendChild(li);
        }
    }

    async renderArticle(article) {
        this.closeSearchPanel();
        if (!article) {
            this.state.currentArticle = null;
            this.state.isEditing = false;
            this.state.currentArticleContent = "";
            this.title.setParts({ action: _t("Espacio de Trabajo") });
            return;
        }

        // Reset cover state
        this.state.isRepositioning = false;

        // Check if we are switching articles to reset editing state
        if (this.state.currentArticleId !== article.id) {

            // Sync current changes before switching
            if (this.state.saveStatus === 'dirty' && this.wysiwyg) {
                await this.saveArticle();
            }

            if (this.contentObserver) {
                this.contentObserver.disconnect();
                this.contentObserver = null;
            }

            this.state.isEditing = false;
            this.wysiwyg = null;
        }

        if (article && !article.active && !this.state.showArchived) {
            this.state.isActive = false;
            this.state.currentArticle = null;
            return;
        }

        // Update core identification state
        this.state.currentArticle = article;
        this.state.currentArticleName = article.name;
        this.title.setParts({ action: article.name });
        localStorage.setItem("last_article_name", article.name);
        this.state.currentArticleId = article.id;
        this.state.isActive = article.active;
        this.state.currentArticleContent = ""; // Clear content while loading

        // Update counts and social
        this.state.viewsCount = article.views_count || 0;
        this.state.likesCount = article.likes_count || 0;
        this.state.likedByIds = article.liked_by_ids || [];

        localStorage.setItem("last_article_id", article.id);

        const currentHash = window.location.hash;
        const newHash = this._updateUrlParam(currentHash, 'article_id', article.id);
        history.replaceState(null, '', newHash);

        const trail = this.getBreadcrumbTrail(article.id) || [];
        this.state.breadcrumbTrail = trail;

        // Tree management
        let parentId = article.parent_id;
        while (parentId) {
            const parent = this.articles.find(a => a.id === parentId);
            if (parent) {
                parent.expanded = true;
                parentId = parent.parent_id;
            } else break;
        }
        this._refreshTree(this.isFilteredView);

        setTimeout(() => {
            const selected = this.root.el.querySelector(".tree-node.selected-row");
            if (selected) selected.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 100);

        // Content Loading Logic
        try {
            if (!this.articleContentCache.has(article.id)) {
                const [rec] = await this.orm.read("knowledge.article", [article.id], [
                    "content", "cover_image_type", "cover_image_url", "cover_image_binary", "cover_position", "icon"
                ]);
                const html = rec.content || "";

                // Update the article object with fetched metadata so it's available in state
                const updates = {
                    cover_image_type: rec.cover_image_type,
                    cover_image_url: rec.cover_image_url,
                    cover_image_binary: rec.cover_image_binary,
                    cover_position: rec.cover_position || 0,
                    icon: rec.icon
                };
                Object.assign(article, updates);

                if (this.state.currentArticle && this.state.currentArticle.id === article.id) {
                    Object.assign(this.state.currentArticle, updates);
                }

                this.articleContentCache.set(article.id, {
                    html,
                    text: "",
                    cover_image_type: rec.cover_image_type,
                    cover_image_url: rec.cover_image_url,
                    cover_image_binary: rec.cover_image_binary,
                    cover_position: rec.cover_position,
                    icon: rec.icon
                });
                toTextAsync(html, (txt) => {
                    const cached = this.articleContentCache.get(article.id);
                    if (cached) cached.text = txt;
                });
            }

            const currentCached = this.articleContentCache.get(article.id);
            const contentToSet = currentCached.html || "";

            // VERIFICATION: Only update if the article_id matches (to avoid race conditions)
            if (this.state.currentArticleId === article.id) {
                this.state.currentArticleContent = contentToSet;
                this._lastSavedContent = contentToSet; // Initialize for comparison
            } else {
            }
        } catch (error) {
            this.state.currentArticleContent = "<p class='text-danger'>Error al cargar el contenido.</p>";
        }

        this.state.favoriteMap[article.id] = !!this.state.favoriteMap[article.id];

        // Ensure we are in edit mode after loading with a tiny delay to force Owl re-evaluation
        setTimeout(() => {
            if (this.state.currentArticleId === article.id) {
                this.state.isEditing = true;
            }
        }, 10);

        const createdUserTuple = article.create_uid || [];
        const modifiedUserTuple = article.write_uid || [];
        const createdUserId = createdUserTuple[0];
        const modifiedUserId = modifiedUserTuple[0];

        this.state.createdBy = createdUserTuple[1] || "";
        this.state.createdByAvatar = createdUserId ? `/web/image/res.users/${createdUserId}/image_128` : "";
        this.state.createdOn = article.create_date;
        this.state.createdAgo = getTimeAgo(article.create_date);

        this.state.modifiedBy = modifiedUserTuple[1] || "";
        this.state.modifiedByAvatar = modifiedUserId ? `/web/image/res.users/${modifiedUserId}/image_128` : "";
        this.state.modifiedOn = article.write_date;
        this.state.modifiedAgo = getTimeAgo(article.write_date);



        if (!this.viewedArticles.has(article.id)) {
            this.viewedArticles.add(article.id);
            sessionStorage.setItem("viewedArticles", JSON.stringify([...this.viewedArticles]));
            setTimeout(async () => {
                try {
                    await this.rpc("/knowledge/article/increment_view", { article_id: article.id });
                } catch (e) {
                    console.warn("Failed to update view count", e);
                }
            }, 1000);
        }

        if (article) {
            const hist = this.state.articleHistory;
            const idx = this.state.historyIndex;
            // Only push if it's not a back/forward action and it's a different article
            if (article.id !== hist[idx]?.id) {
                const newHist = hist.slice(0, idx + 1);
                newHist.push(article);
                this.state.articleHistory = newHist;
                this.state.historyIndex = newHist.length - 1;
            }
        }

        this._loadChatter(article);
    }

    goBack() {
        if (this.state.historyIndex > 0) {
            this.state.historyIndex--;
            const article = this.state.articleHistory[this.state.historyIndex];
            this.renderArticle(article);
        }
    }

    goForward() {
        if (this.state.historyIndex < this.state.articleHistory.length - 1) {
            this.state.historyIndex++;
            const article = this.state.articleHistory[this.state.historyIndex];
            this.renderArticle(article);
        }
    }

    editArticle() {
        if (!this.state.currentArticle) return;
        this.state.isEditing = true;
    }

    async saveArticle() {
        if (!this.state.currentArticle || !this.wysiwyg) return;

        if (this._isSaving) {
            this._pendingSave = true;
            return;
        }

        this._isSaving = true;
        try {
            let lastSavedContent = null;
            do {
                this._pendingSave = false;
                const newContent = this.wysiwyg.getValue();

                // CRITICAL: Avoid redundant saves if content hasn't changed from what's on server
                if (newContent === this._lastSavedContent) {
                    this.state.saveStatus = 'saved';
                    break;
                }

                // Avoid redundant saves if content hasn't changed since last loop iteration
                if (newContent === lastSavedContent) break;

                this.state.saveStatus = 'saving';

                await this.orm.write("knowledge.article", [this.state.currentArticle.id], {
                    content: newContent
                });

                this.articleContentCache.set(this.state.currentArticle.id, {
                    html: newContent,
                    text: "",
                    cover_image_type: this.state.currentArticle.cover_image_type,
                    cover_image_url: this.state.currentArticle.cover_image_url,
                    cover_image_binary: this.state.currentArticle.cover_image_binary,
                    cover_position: this.state.currentArticle.cover_position,
                    icon: this.state.currentArticle.icon
                });
                lastSavedContent = newContent;
                this._lastSavedContent = newContent; // Update server-sync reference

                this.state.saveStatus = 'saved';
            } while (this._pendingSave);

        } catch (error) {
            console.error("Error en auto-guardado:", error);
            this.state.saveStatus = 'dirty';
            this.notification.add(_t("Error al guardar cambios automáticamente."), { type: "danger" });
        } finally {
            this._isSaving = false;
        }
    }

    cancelEdit() {
        this.state.isEditing = false;
        this.wysiwyg = null;
        this.renderArticle(this.state.currentArticle);
    }

    _bindUI() {
        const sidebarSearchInput = this.root.el.querySelector(".o_article_search_input");
        const matchCount = this.root.el.querySelector(".o_article_match_count");
        const clearIcon = this.root.el.querySelector(".o_clear_search");

        if (sidebarSearchInput) {
            sidebarSearchInput.addEventListener("input", () => {
                const q = sidebarSearchInput.value.toLowerCase();
                this.searching = !!q;

                if (!q) {
                    this.filteredArticles = [];
                    if (matchCount) matchCount.classList.add("d-none");
                    if (clearIcon) clearIcon.classList.add("d-none");
                    this._refreshTree(false);
                    return;
                }

                if (clearIcon) clearIcon.classList.remove("d-none");
                this.filteredArticles = this._getFilteredWithAncestors(q);
                if (matchCount) {
                    matchCount.textContent = `${this.filteredArticles.length} match${this.filteredArticles.length !== 1 ? 'es' : ''} found`;
                    matchCount.classList.remove("d-none");
                }
                this._refreshTree(true);
            });

            if (clearIcon) {
                clearIcon.addEventListener("click", () => {
                    sidebarSearchInput.value = "";
                    this.filteredArticles = [];
                    this.searching = false;
                    if (clearIcon) clearIcon.classList.add("d-none");
                    if (matchCount) matchCount.classList.add("d-none");
                    this._refreshTree(false);
                });
            }
        }
    }

    _getFilteredWithAncestors(query) {
        const q = (query || "").toLowerCase();
        const deep = !!this.state.searchInContent;

        const matches = this.articles.filter(a => {
            if ((a.name || "").toLowerCase().includes(q)) return true;
            if (!deep) return false;
            const cached = this.articleContentCache.get(a.id);
            return !!cached && !!cached.text && cached.text.includes(q);
        });

        const result = new Set(matches);
        for (const article of matches) {
            let parentId = article.parent_id;
            while (parentId) {
                const parent = this.articles.find(a => a.id === parentId);
                if (parent && !result.has(parent)) {
                    result.add(parent);
                    parentId = parent.parent_id;
                } else break;
            }
        }
        return Array.from(result);
    }

    async loadTags() {
        const tags = await this.orm.searchRead("knowledge.tag", [], ["id", "name"]);
        this.state.availableTags = tags;
        this.tagIdToName = new Map(tags.map(t => [t.id, t.name]));
    }

    _initSplitter() {
        const splitter = this.splitter.el;
        const sidebar = this.root.el.querySelector(".o_knowledge_sidebar");

        let isDragging = false;

        splitter.addEventListener("mousedown", (e) => {
            if (e.target.closest(".o_sidebar_patch")) return;
            if (this.state.sidebarCollapsed) return;

            isDragging = true;
            document.body.style.cursor = "ew-resize";
            e.preventDefault();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const offsetLeft = e.clientX;
            if (offsetLeft > 150 && offsetLeft < 600) {
                sidebar.style.width = offsetLeft + "px";
            }
        });

        document.addEventListener("mouseup", () => {
            if (isDragging) {
                isDragging = false;
                document.body.style.cursor = "";
                const w = Math.round(sidebar.getBoundingClientRect().width);
                if (w >= 150 && w <= 600) {
                    localStorage.setItem("sidebar_width", String(w));
                }
            }
        });
    }

    _newArticleAutoFocus() {
        document.addEventListener("transitionend", (e) => {
            if (this.state.showNewArticlePanel && e.target.classList.contains("new-article-panel")) {
                const input = this.root.el.querySelector("#new_article_input");
                if (input) input.focus();
            }
        });
    }

    _saveOnEnter() {
        setTimeout(() => {
            const input = this.root.el.querySelector("#new_article_input");
            if (input) input.focus();
        }, 0);

        this.root.el.querySelector("#new_article_input")?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                this.createQuickArticle();
            }
        });
    }

    _onGlobalClick(e) {
        const bcNode = e.target.closest("[data-id]");
        if (bcNode) {
            const id = parseInt(bcNode.dataset.id);
            const article = this.articles.find(a => a.id === id);
            if (article) return this.renderArticle(article);
        }

        const card = this.cardPanel?.el;
        const toggle = this.cardToggleIcon?.el;

        if (!card || !this.state.showCardPanel) return;

        const clickedInsideCard = card.contains(e.target);
        const clickedToggle = toggle && toggle.contains(e.target);

        if (!clickedInsideCard && !clickedToggle) {
            this._closeCardPanel();
        }
    }

    _onEscapeKey(e) {
        if (e.key !== "Escape") return;

        const el = document.activeElement;
        if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) {
            el.blur();
        }

        const closedSomething = this._closeAllOverlays();
        if (closedSomething) {
            e.preventDefault();
            e.stopPropagation();
        }
    }

    _closeAllOverlays() {
        let closed = false;
        const close = (cond, action) => {
            if (!cond) return;
            closed = true;
            if (typeof action === "function") action();
            else this.state[action] = false;
        };

        close(this.state.showCardPanel, () => this._closeCardPanel());

        close(this.state.showSearchPanel, () =>
            this.closeSearchPanel ? this.closeSearchPanel() : (this.clearSearch?.(), this.state.showSearchPanel = false)
        );

        close(this.state.showFilterOverlay, "showFilterOverlay");

        close(this.state.showVersionHistoryPanel, "showVersionHistoryPanel");
        close(this.state.showDiffPanel, () => this.closeDiffPanel && this.closeDiffPanel());

        close(this.state.showNewArticlePanel, "showNewArticlePanel");

        close(this.state.showRenameModal, "showRenameModal");
        close(this.state.showMoveModal, "showMoveModal");
        close(this.state.showArchiveModal, "showArchiveModal");
        close(this.state.showUnarchiveModal, "showUnarchiveModal");
        close(this.state.showCopyModal, "showCopyModal");
        close(this.state.showTagModal, "showTagModal");
        close(this.state.showDropdown, "showDropdown");
        close(this.state.showMoreOptions, "showMoreOptions");

        if (closed);
        return closed;
    }

    async _loadChatter(article) {
        this.state.currentArticle = article;
        this._renderComments();
    }

    async _renderComments() {
        const container = this.root.el.querySelector(".comment-list");
        if (!container || !this.state.currentArticle) return;

        const messages = await this.rpc(`/knowledge/article/${this.state.currentArticle.id}/messages`, {});
        const threadMap = new Map();

        for (const msg of messages) {
            msg.children = [];
            threadMap.set(msg.id, msg);
        }

        for (const msg of messages) {
            if (msg.parent_id && threadMap.has(msg.parent_id)) {
                threadMap.get(msg.parent_id).children.push(msg);
            }
        }

        const topLevel = messages.filter(msg => !msg.parent_id);

        container.innerHTML = "";
        for (const msg of topLevel) {
            container.appendChild(this._renderMessageThread(msg));
        }

        const topBox = document.createElement("div");
        topBox.className = "o_comment_box mt-3";
        topBox.innerHTML = `
            <textarea class="form-control comment-input mb-2" placeholder="Add a comment..."></textarea>
            <button class="btn btn-primary">
                <span class="spinner-border spinner-border-sm d-none me-2" role="status" aria-hidden="true"></span>
                <span>Post</span>
            </button>
        `;
        topBox.querySelector(".btn-primary").addEventListener("click", () => {
            this.postComment(null, topBox);
        });
        container.appendChild(topBox);

    }

    _renderMessageThread(msg) {
        const wrapper = document.createElement("div");
        wrapper.className = "comment border rounded p-2 mb-2";
        const msgCreatedAgo = getTimeAgo(msg.date);

        wrapper.innerHTML = `
            <strong>${msg.author}</strong>
            <div class="text-muted small">${msgCreatedAgo}</div>
            <div>${msg.body}</div>
            <button class="btn btn-link p-0 mt-1 reply-btn">Reply</button>
            <div class="reply-section d-none mt-2">
                <textarea class="form-control reply-input mb-1" data-parent-id="${msg.id}"></textarea>
                <button class="btn btn-sm btn-primary">Post</button>
            </div>
        `;

        const replyBtn = wrapper.querySelector(".reply-btn");
        const replySection = wrapper.querySelector(".reply-section");
        const postBtn = replySection.querySelector(".btn-primary");

        replyBtn.addEventListener("click", () => replySection.classList.toggle("d-none"));
        postBtn.addEventListener("click", (e) => {
            const wrapper = e.target.closest(".reply-section");
            this.postComment(msg.id, wrapper);
        });
        postBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm d-none me-2" role="status" aria-hidden="true"></span>
            <span>Post</span>
        `;

        if (msg.children.length) {
            const childContainer = document.createElement("div");
            childContainer.className = "child-comments ps-4";

            for (const child of msg.children) {
                const childThread = this._renderMessageThread(child);
                childContainer.appendChild(childThread);
            }

            wrapper.appendChild(childContainer);
        }

        return wrapper;
    }

    async postComment(parent_id = null, section = null) {
        const root = this.root.el;
        const input = section?.querySelector("textarea.comment-input, textarea.reply-input");
        const postBtn = section?.querySelector(".btn-primary");
        const spinner = postBtn?.querySelector(".comment-list");

        if (!input) {
            console.warn("Comment textarea not found");
            return;
        }

        const content = input.value.trim();
        if (!content) {
            console.warn("Comment is empty");
            return;
        }

        if (spinner) spinner.classList.remove("d-none");
        if (postBtn) postBtn.disabled = true;
        this.state.commentLoading = true;

        const parsedParentId = parseInt(parent_id);
        const isReply = !isNaN(parsedParentId) && parsedParentId > 0;

        const kwargs = {
            body: content,
            message_type: "comment",
        };

        if (isReply) {
            kwargs.parent_id = parsedParentId;
        }

        try {
            const message_id = await this.rpc("/web/dataset/call_kw", {
                model: "knowledge.article",
                method: "message_post",
                args: [this.state.currentArticle.id],
                kwargs,
            });

            input.value = "";
            await this._renderComments();
            this._showToast("Comment added successfully.");
        } catch (e) {
            console.error("Error posting comment", e);
        } finally {
            if (spinner) spinner.classList.add("d-none");
            if (postBtn) postBtn.disabled = false;
            this.state.commentLoading = false;
        }
    }

    async toggleFavorite() {
        const articleId = this.state.currentArticleId;
        if (!articleId) return;
        try {
            const res = await this.orm.call("knowledge.article", "action_toggle_favorite", [articleId]);
            this.state.favoriteMap[articleId] = !!res.favorite;
            this._refreshTree(this.isFilteredView);
            ;
        } catch (e) {
            console.error("toggleFavorite failed", e);
            this._showToast("Could not update favorite.", "error");
        }
    }

    async toggleTag(tag) {
        const tagId = tag.name;
        if (this.state.selectedTags.includes(tagId)) {
            this.state.selectedTags = this.state.selectedTags.filter(t => t !== tagId);
        } else {
            this.state.selectedTags.push(tagId);
        }
        this.filterArticles();
    }

    onSearchInput(ev) {
        this.state.query = ev.target.value;
        this.debouncedSearch();
    }

    async _performSearch() {
        const raw = this.state.query || "";
        const query = raw.trim().toLowerCase();

        if (!query) {
            this.state.searchResults = [];
            return;
        }

        const source = this.articles || [];

        if (!this.state.searchInContent) {
            this.state.searchResults = source
                .filter(a => (a.name || "").toLowerCase().includes(query))
                .map(a => ({ ...a, snippet: "" }));
            return;
        }

        const MAX_BATCH = 200;
        const missingIds = [];
        for (const a of source) {
            if (!this.articleContentCache.has(a.id)) {
                missingIds.push(a.id);
                if (missingIds.length >= MAX_BATCH) break;
            }
        }

        if (missingIds.length) {
            try {
                const recs = await this.orm.read("knowledge.article", missingIds, ["content"]);
                for (let i = 0; i < recs.length; i++) {
                    const html = recs[i]?.content || "";
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, "text/html");
                    const text = (doc.body?.textContent || "").toLowerCase();
                    this.articleContentCache.set(missingIds[i], { html, text });
                }
            } catch (e) {
                console.warn("Content batch read failed:", e);
            }
        }

        const results = [];
        for (const a of source) {
            const name = (a.name || "").toLowerCase();
            const nameMatch = name.includes(query);

            const cached = this.articleContentCache.get(a.id);
            const text = cached?.text || "";
            const contentMatch = text ? text.includes(query) : false;

            if (nameMatch || contentMatch) {
                let snippet = "";
                if (text) {
                    const idx = text.indexOf(query);
                    if (idx !== -1) {
                        const start = Math.max(0, idx - 40);
                        const end = idx + query.length + 40;
                        snippet = "... " + text.slice(start, end).trim() + " ...";
                    }
                }
                results.push({ ...a, snippet });
            }
        }

        this.state.searchResults = results;
    }

    clearSearch() {
        this.state.query = "";
        this.state.searchResults = [];

        const inputEl = this.root.el.querySelector(".o_slide_search_input");
        if (inputEl) {
            inputEl.value = "";
        }


    }

    openSearchPanel() {
        this.state.showSearchPanel = true;
        this.clearSearch();
        setTimeout(() => {
            this.root.el.querySelector(".o_slide_search_input")?.focus();
        }, 0);
    }

    closeSearchPanel() {
        this.clearSearch();
        this.state.showSearchPanel = false;
    }

    toggleMetadata() {
        this.state.showMetadata = !this.state.showMetadata;
    }

    toggleMoreOptions() {
        this.state.showMoreOptions = !this.state.showMoreOptions;
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString();
    }

    onTagFilterChange(ev) {
        const selectedOptions = [...ev.target.options]
            .filter(opt => opt.selected)
            .map(opt => opt.value);
        this.state.selectedTags = selectedOptions.map(id => parseInt(id));
        localStorage.setItem("selected_tags", JSON.stringify(this.state.selectedTags));
        localStorage.setItem("only_favorites", this.state.onlyFavorites ? "1" : "0");
        this.filterArticles();
    }

    filterArticles() {
        const base = [...this.allArticles];

        let result = [];
        if (this.state.showArchived) {
            const archived = base.filter(r => !r.active);
            const idsToInclude = new Set(archived.map(r => r.id));
            const idMap = new Map(base.map(r => [r.id, r]));

            for (const article of archived) {
                let parentId = article.parent_id;
                while (parentId) {
                    const parent = idMap.get(parentId);
                    if (parent && !idsToInclude.has(parent.id)) {
                        idsToInclude.add(parent.id);
                        parentId = parent.parent_id;
                    } else break;
                }
            }
            result = base.filter(r => idsToInclude.has(r.id));
        } else {
            // STRICT HIERARCHY CHECK: If an ancestor is archived, the child must be hidden too.
            const idMap = new Map(base.map(r => [r.id, r]));
            result = base.filter(r => {
                if (!r.active) return false;

                let parentId = r.parent_id;
                while (parentId) {
                    const parent = idMap.get(parentId);
                    if (!parent) break;
                    if (!parent.active) return false; // Ancestor is archived -> hide branch
                    parentId = parent.parent_id;
                }
                return true;
            });
        }

        const selectedTags = this.state.selectedTags;
        const onlyFav = this.state.onlyFavorites;

        const matches = result.filter(article => {
            const tagMatch = !selectedTags.length || article.tag_ids_raw?.some(tagId => selectedTags.includes(tagId));
            const favMatch = !onlyFav || this.state.favoriteMap[article.id];
            return tagMatch && favMatch;
        });

        for (const a of base) delete a.isTagMatch;
        for (const article of matches) {
            if (selectedTags.length && article.tag_ids_raw?.some(tagId => selectedTags.includes(tagId))) {
                article.isTagMatch = true;
            }
        }

        const finalSet = new Set(matches);
        const fullMap = new Map(base.map(r => [r.id, r]));
        for (const article of matches) {
            let parentId = article.parent_id;
            while (parentId) {
                const parent = fullMap.get(parentId);
                if (parent && !finalSet.has(parent)) {
                    finalSet.add(parent);
                    parentId = parent.parent_id;
                } else break;
            }
        }
        const final = Array.from(finalSet);

        for (const article of final) {
            let parentId = article.parent_id;
            while (parentId) {
                const parent = fullMap.get(parentId);
                if (parent) {
                    parent.expanded = true;
                    parentId = parent.parent_id;
                } else break;
            }
        }

        this.articles = final;
        this.filteredArticles = final;

        this.sortFilteredArticles();

        const curId = this.state.currentArticleId;
        const stillVisible = final.find(a => a.id === curId);

        if (final.length === 0) {
            this.state.currentArticle = null;
            this.state.currentArticleId = null;
            this.renderArticle(null);
        } else if (!stillVisible && !this.state.isLoading) {
            const next = final[0];
            this.renderArticle(next);
        } else {
            this.renderArticle(stillVisible);
        }

        this._refreshTree(true);

        localStorage.setItem("selected_tags", JSON.stringify(this.state.selectedTags));
        localStorage.setItem("only_favorites", this.state.onlyFavorites ? "1" : "0");
        localStorage.setItem("show_archived", this.state.showArchived ? "1" : "0");
    }

    exportArticle() {
        if (!this.state.currentArticle) return;

        const contentDiv = document.createElement("div");
        contentDiv.innerHTML = `
            <div style="font-family: 'Segoe UI', sans-serif; padding: 20px;">
                <h1>${this.state.currentArticle.name}</h1>
                <p style="font-size: 12px; color: #666;">
                    Created by ${this.state.createdBy} · ${new Date(this.state.createdOn).toLocaleString()}<br>
                    Last edited by ${this.state.modifiedBy} · ${new Date(this.state.modifiedOn).toLocaleString()}
                </p>
                <hr style="margin: 12px 0;">
                ${this.state.currentArticle.content}
            </div>
        `;

        const opt = {
            margin: 0.5,
            filename: `${this.state.currentArticle.name.replace(/[^a-z0-9]/gi, '_')}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2 },
            jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(contentDiv).save();
        this._showToast("Article exported successfully.");
    }

    toggleSharePanel() {
        if (!this.state.currentArticle) return;
        this.state.showSharePanel = !this.state.showSharePanel;
    }

    async togglePublish() {
        if (!this.state.currentArticle) return;
        const newValue = !this.state.currentArticle.is_published;
        const recursive = this.state.recursivePublish;

        if (recursive) {
            await this.orm.call("knowledge.article", "action_publish_tree", [[this.state.currentArticleId]], {
                publish: newValue
            });
        } else {
            await this.orm.write("knowledge.article", [this.state.currentArticleId], {
                is_published: newValue
            });
        }

        // Update local state
        this.state.currentArticle.is_published = newValue;

        const status = newValue ? "Published" : "Unpublished";
        const mode = recursive ? "(Recursive)" : "";
        this._showToast(`Article ${status} ${mode} successfully.`);
    }

    async toggleRecursive() {
        this.state.recursivePublish = !this.state.recursivePublish;
        // If article is currently published and we turn ON recursion, apply it immediately
        if (this.state.currentArticle.is_published && this.state.recursivePublish) {
            await this.orm.call("knowledge.article", "action_publish_tree", [[this.state.currentArticleId]], {
                publish: true
            });
            this._showToast("Sub-pages published.");
        }
    }

    shareArticleLink() {
        if (!this.state.currentArticleId || !this.state.currentArticle?.share_token) return;

        const url = `${window.location.origin}/knowledge/article/${this.state.currentArticle.share_token}`;

        navigator.clipboard.writeText(url).then(() => {
            this.state.showCopied = true;
            setTimeout(() => {
                this.state.showCopied = false;
            }, 2000);
            this._showToast("Link copied to clipboard.");
        }).catch(err => {
            console.error("Clipboard copy failed:", err);
            this._showToast("Failed to copy link.");
        });
    }
    onGlobalClick(ev) {
        if (this.state.showSharePanel) {
            // Check if the click is inside the popover or on the toggle button
            // We can assume the popover has a specific class .o_knowledge_share_popover
            const inPopover = ev.target.closest(".o_knowledge_share_popover");
            const onButton = ev.target.closest(".btn-outline-secondary[t-on-click='toggleSharePanel']"); // Heuristic, might need ref if possible, but class selection is safer for now if ref not avail
            // Actually, better: if we can't easily find the button by ref, we check closest.
            // But let's check checking if NOT inside popover container
            if (!inPopover && !ev.target.closest('[t-on-click="toggleSharePanel"]')) {
                this.state.showSharePanel = false;
            }
        }
    }

    async openVersionHistory() {
        this.state.showVersionHistoryPanel = true;
        let versions = await this.orm.searchRead("knowledge.article.version", [
            ["article_id", "=", this.state.currentArticleId]
        ], ["id", "version_number", "create_date", "user_id"], { order: "version_number desc" });

        // Añadir una entrada virtual para el estado actual
        const currentVersionEntry = {
            id: 'current',
            version_number: this.state.currentArticle.version,
            create_date: _t("Hoy (Actual)"),
            user_id: [0, _t("Usted")],
            is_current: true
        };

        this.state.versionHistory = [currentVersionEntry, ...versions];
        this.state.historyTab = 'content';
        await this.selectHistoryVersion('current');
    }

    async selectHistoryVersion(versionId) {
        this.state.selectedVersionId = versionId;
        this.state.diffHtml = null; // Limpiar diff previo al cambiar de versión

        if (versionId === 'current') {
            const article = this.state.currentArticle;
            this.state.selectedVersionContent = this.wysiwyg ? this.wysiwyg.getValue() : (this.state.currentArticleContent || "");
            this.state.selectedVersionMetadata = {
                name: article.name,
                icon: article.icon,
                cover_image_type: article.cover_image_type,
                cover_image_url: article.cover_image_url,
                cover_image_binary: article.cover_image_binary,
                cover_position: article.cover_position,
                version_number: article.version
            };
        } else {
            const [version] = await this.orm.read("knowledge.article.version", [versionId], [
                "content", "version_number", "name", "icon", "cover_image_type", "cover_image_url", "cover_image_binary", "cover_position"
            ]);
            this.state.selectedVersionContent = version.content;
            this.state.selectedVersionMetadata = version;
        }

        // Cargar diff si estamos en esa pestaña
        if (this.state.historyTab === 'diff') {
            await this.loadVersionDiff();
        }
    }

    async setHistoryTab(tab) {
        this.state.historyTab = tab;
        if (tab === 'diff') {
            await this.loadVersionDiff();
        }
    }

    async loadVersionDiff() {
        const versionId = this.state.selectedVersionId;
        if (!versionId) return;

        // Si es la versión actual, el diff es vacío o informativo
        if (versionId === 'current') {
            this.state.diffHtml = `<div class="p-5 text-center text-muted">
                <i class="fa fa-info-circle fa-2x mb-3"></i>
                <p>${_t("Estás viendo el estado actual del artículo. Selecciona una versión anterior en la izquierda para ver qué ha cambiado respecto a lo que tienes ahora.")}</p>
            </div>`;
            return;
        }

        // Comparar la versión seleccionada contra el artículo "EN VIVO"
        const [wizard] = await this.orm.create('knowledge.version.compare.wizard', [{
            article_id: this.state.currentArticleId,
            old_version_id: versionId
        }]);

        const [record] = await this.orm.read('knowledge.version.compare.wizard', [wizard], ['diff_html']);

        // Verificación de seguridad: ¿sigue siendo esta la versión seleccionada?
        if (this.state.selectedVersionId === versionId) {
            this.state.diffHtml = record.diff_html;
        }
    }

    async restoreSelectedVersion() {
        if (!this.state.selectedVersionId || this.state.selectedVersionId === 'current') return;

        const success = await this.orm.call("knowledge.article", "action_restore_version", [this.state.currentArticleId, this.state.selectedVersionId]);
        if (success) {
            this.state.showVersionHistoryPanel = false;
            this._showToast("Versión restaurada con éxito.");

            // Forzar recarga completa limpiando caché
            this.articleContentCache.delete(this.state.currentArticleId);
            await this.renderArticle(this.state.currentArticle);
        }
    }

    get markup() {
        return markup;
    }

    async openDiffPanel(oldId, currentId) {
        const [wizard] = await this.orm.create('knowledge.version.compare.wizard', [{
            article_id: this.state.currentArticleId,
            old_version_id: oldId,
            current_version_id: currentId,
        }]);

        const [record] = await this.orm.read('knowledge.version.compare.wizard', [wizard], ['diff_html']);
        this.state.diffHtml = record.diff_html;
        this.state.oldVersionId = oldId;
        this.state.currentVersionId = currentId;
        this.state.showDiffPanel = true;
    }

    closeDiffPanel() {
        this.state.showDiffPanel = false;
        this.state.diffHtml = '';
        this.state.oldVersionId = null;
        this.state.currentVersionId = null;
    }

    async createCopy() {
        if (!this.state.currentArticle) return;

        const [original] = await this.orm.read("knowledge.article", [this.state.currentArticle.id], ["name"]);
        this.state.copyTitle = original.name + " (copy)";
        this.state.showCopyModal = true;
    }

    cancelCopy() {
        this.state.showCopyModal = false;
        this.state.copyTitle = '';
    }

    async confirmCopy() {
        const newName = this.state.copyTitle.trim();
        if (!newName) {
            alert("Name cannot be empty.");
            return;
        }

        try {
            const [original] = await this.orm.read("knowledge.article", [this.state.currentArticle.id], [
                "content", "tag_ids", "parent_id", "is_published"
            ]);

            const [newId] = await this.orm.create("knowledge.article", [{
                name: newName,
                content: original.content,
                tag_ids: original.tag_ids.map(id => [4, id]),
                parent_id: original.parent_id?.[0] || false,
                is_published: original.is_published,
                active: true,
            }]);

            await this.loadArticles();
            const newArticle = this.articles.find(a => a.id === newId);
            if (newArticle) this.renderArticle(newArticle);

            this._showToast("Article copied successfully.");
        } catch (err) {
            console.error("Failed to copy article:", err);
            alert("Failed to copy article.");
        } finally {
            this.state.showCopyModal = false;
            this.state.copyTitle = '';
        }
    }

    _showToast(message = "", type = "success") {
        const toast = document.createElement("div");
        toast.className = "toast-message";
        toast.innerText = message;

        const colors = {
            info: "#333",       // default
            success: "#28a745", // green
            warning: "#ffc107", // orange
            error: "#dc3545",   // red
        };

        const bg = colors[type] || colors.info;

        Object.assign(toast.style, {
            position: "fixed",
            bottom: "20px",
            right: "20px",
            background: bg,
            color: "#fff",
            padding: "10px 20px",
            borderRadius: "5px",
            zIndex: 9999,
            opacity: 0,
            transition: "opacity 0.3s ease-in-out",
        });

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = 1;
        }, 100);

        setTimeout(() => {
            toast.style.opacity = 0;
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 2500);
    }

    openRenameModal() {
        this.state.renameTitle = this.state.currentArticleName;
        this.state.showRenameModal = true;
    }

    cancelRename() {
        this.state.showRenameModal = false;
        this.state.renameTitle = '';
    }

    async confirmRename() {
        const newTitle = this.state.renameTitle.trim();
        if (!newTitle || newTitle === this.state.currentArticleName) {
            this.state.showRenameModal = false; return;
        }
        await this._saveNewTitle(newTitle);
        this.state.showRenameModal = false;
    }

    async onTitleBlur(ev) {
        const newTitle = ev.target.value.trim();
        if (!newTitle || newTitle === this.state.currentArticleName) {
            ev.target.value = this.state.currentArticleName;
            return;
        }
        await this._saveNewTitle(newTitle);
    }

    onTitleKeydown(ev) {
        if (ev.key === "Enter") {
            ev.target.blur();
        } else if (ev.key === "Escape") {
            ev.target.value = this.state.currentArticleName;
            ev.target.blur();
        }
    }

    async _saveNewTitle(newTitle) {
        try {
            await this.orm.write("knowledge.article", [this.state.currentArticleId], { name: newTitle });
            const item = this.allArticles.find(a => a.id === this.state.currentArticleId);
            if (item) item.name = newTitle;
            if (this.state.currentArticle) {
                this.state.currentArticle.name = newTitle;
                this.state.currentArticleName = newTitle;
                this.title.setParts({ action: newTitle });
                localStorage.setItem("last_article_name", newTitle);
            }
            this._refreshTree(this.isFilteredView);
            this._showToast("Artículo renombrado.");
        } catch (e) {
            console.error("Failed to rename article", e);
            this._showToast("Error al renombrar artículo.", "error");
        }
    }

    moveToFolder() {
        this.state.moveTargetId = this.state.currentArticle.parent_id || null;
        this.state.selectedMoveTarget = this.state.currentArticle.parent_id || null;
        this.state.showMoveModal = true;
    }

    cancelMove() {
        this.state.showMoveModal = false;
        this.state.moveTargetId = null;
        this.state.selectedMoveTarget = null;
    }

    selectMoveTarget(articleId) {
        this.state.moveTargetId = articleId;
        this.state.selectedMoveTarget = articleId;
    }

    async confirmMove() {
        await this.orm.write("knowledge.article", [this.state.currentArticleId], { parent_id: this.state.moveTargetId });
        const item = this.allArticles.find(a => a.id === this.state.currentArticleId);
        if (item) item.parent_id = this.state.moveTargetId || null;
        this.filterArticles();
        this.renderArticle(item);
        this.state.showMoveModal = false;
        this._showToast("Article moved successfully.");
    }

    getBreadcrumbTrail(articleId) {
        const trail = [];
        let current = this.articles.find(a => a.id === articleId);
        while (current) {
            trail.unshift(current);
            current = this.articles.find(a => a.id === current.parent_id);
        }
        return trail;
    }

    handleBreadcrumbClick(ev) {
        const target = ev.target.closest('[data-id]');
        if (!target) return;

        const id = parseInt(target.dataset.id);
        if (!isNaN(id)) {
            const article = this.articles.find(a => a.id === id);
            if (article) this.renderArticle(article);
        }
    }

    _onTreeToggleClick(ev) {
        const icon = ev.target.closest(".tree-toggle-icon");
        if (!icon) return;

        const li = icon.closest("li.tree-item");
        if (!li) return;

        const articleId = parseInt(li.dataset.articleId);
        const article = this.articles.find(a => a.id === articleId);
        if (!article) return;

        article.expanded = !article.expanded;
        localStorage.setItem("expanded_nodes", JSON.stringify(
            this.articles.filter(a => a.expanded).map(a => a.id)
        ));
        this._refreshTree(this.isFilteredView);
    }

    openTagModal() {
        if (!this.state.currentArticle) return;
        this.state.showTagModal = true;
        this.state.tagSearch = '';
        this.state.selectedTagIds = [...(this.state.currentArticle?.tag_ids_raw || [])];
    }

    cancelTagModal() {
        this.state.showTagModal = false;
        this.state.selectedTagIds = [];
    }

    toggleTagSelection(tagId) {
        const id = parseInt(tagId);
        const list = this.state.selectedTagIds;
        if (list.includes(id)) {
            this.state.selectedTagIds = list.filter(x => x !== id);
        } else {
            this.state.selectedTagIds = [...list, id];
        }
    }

    filteredAvailableTags() {
        const query = this.state.tagSearch.toLowerCase();
        return this.state.availableTags.filter(tag => tag.name.toLowerCase().includes(query));
    }

    async confirmTagsUpdate() {
        const ids = this.state.selectedTagIds.map(Number);
        await this.orm.write("knowledge.article", [this.state.currentArticle.id], { tag_ids: [6, 0, ids] });

        const item = this.allArticles.find(a => a.id === this.state.currentArticle.id);
        if (item) {
            item.tag_ids_raw = ids;
            item.tag_ids = ids.map(id => this.tagIdToName.get(id) || "");
        }
        this.filterArticles();
        this.renderArticle(item);
        this.state.showTagModal = false;
        this._showToast("Tag updated successfully.");
    }

    async archiveArticle() {
        const articleId = this.state.currentArticleId;
        const article = this.articles.find(a => a.id === articleId);
        if (!article) return;

        this.state.canArchive = false;

        try {
            const [rec] = await this.orm.read("knowledge.article", [articleId], ["create_uid"]);
            const ownerId = Array.isArray(rec.create_uid) ? Number(rec.create_uid[0]) : NaN;
            const uid = Number(this.user.userId);
            const isOwner = ownerId === uid;
            const isAdmin = !!(await this.user.hasGroup("base.group_system"));

            if (isOwner || isAdmin) {
                this.state.canArchive = true;
                this.state.showArchiveModal = true;
                ;
            } else {
                this._showToast("Only the article owner or Admin can archive this article.", "warning");
            }
        } catch (e) {
            console.error("archiveArticle check failed", e);
        }
    }

    cancelArchive() {
        this.state.showArchiveModal = false;
    }

    async confirmArchive() {
        try {
            const archivedId = this.state.currentArticleId;
            await this.orm.write("knowledge.article", [archivedId], { active: false });
            this.state.showArchiveModal = false;

            const item = this.allArticles.find(a => a.id === archivedId);
            if (item) item.active = false;

            this.articleContentCache.delete(archivedId);

            this.filterArticles();

            if (!this.state.showArchived) {
                const next = this.articles.length ? this.articles[0] : null;
                this.renderArticle(next);
            } else {
                const stillThere = this.articles.find(a => a.id === archivedId) || null;
                this.renderArticle(stillThere);
            }

            this._showToast("Article archived successfully.");
        } catch (err) {
            console.error("Archiving failed", err);
        }
    }

    async unarchiveArticle() {
        const articleId = this.state.currentArticleId;
        const article = this.articles.find(a => a.id === articleId);
        if (!article) return;

        this.state.canUnarchive = false;

        try {
            const [rec] = await this.orm.read("knowledge.article", [articleId], ["create_uid"]);
            const ownerId = Array.isArray(rec.create_uid) ? Number(rec.create_uid[0]) : NaN;
            const uid = Number(this.user.userId);
            const isOwner = ownerId === uid;
            const isAdmin = !!(await this.user.hasGroup("base.group_system"));

            if (isOwner || isAdmin) {
                this.state.canUnarchive = true;
                this.state.showUnarchiveModal = true;
                ;
            } else {
                this._showToast("Only the article owner or Admin can unarchive this article.", "warning");
            }
        } catch (e) {
            console.error("unarchiveArticle check failed", e);
        }
    }

    cancelUnarchive() {
        this.state.showUnarchiveModal = false;
    }

    async confirmUnarchive() {
        try {
            const id = this.state.currentArticleId;
            await this.orm.write("knowledge.article", [id], { active: true });
            this.state.showUnarchiveModal = false;

            const item = this.allArticles.find(a => a.id === id);
            if (item) item.active = true;

            this.filterArticles();

            const cur = this.articles.find(a => a.id === id) || this.articles[0] || null;
            this.renderArticle(cur);

            this._showToast("Article unarchived successfully.");
        } catch (err) {
            console.error("Unarchiving failed", err);
        }
    }


    get isFilteredView() {
        return this.searching || this.state.selectedTags.length > 0 || this.state.onlyFavorites;
    }

    createArticle() {
        this.openNewArticlePanel();
    }

    toggleTag(tag) {
        const tagId = tag.id;
        if (this.state.selectedTags.includes(tagId)) {
            this.state.selectedTags = this.state.selectedTags.filter(tid => tid !== tagId);
        } else {
            this.state.selectedTags.push(tagId);
        }
        this.filterArticles();
    }

    isTagSelected(tagId) {
        return this.state.selectedTags.includes(tagId);
    }

    toggleCollapse(id) {
        if (this.state.collapsedNodes.has(id)) {
            this.state.collapsedNodes.delete(id);
        } else {
            this.state.collapsedNodes.add(id);
        }

    }

    openNewArticlePanel() {
        this.state.showNewArticlePanel = true;
        this.state.newArticleTitle = "";
        this.state.creatingArticle = false;
    }

    cancelNewArticle() {
        this.state.showNewArticlePanel = false;
        this.state.newArticleTitle = "";
    }

    async createQuickArticle() {
        if (this.state.creatingArticle) return;
        const title = this.state.newArticleTitle.trim() || "Sin título";
        this.state.creatingArticle = true;
        try {
            const [newId] = await this.orm.create("knowledge.article", [{
                name: title, parent_id: this.state.currentArticle?.id || false, is_published: true, active: true,
            }]);
            const [rec] = await this.orm.read("knowledge.article", [newId],
                ["id", "name", "parent_id", "tag_ids", "active", "display_name", "views_count", "likes_count", "liked_by_ids", "create_date", "write_date", "create_uid", "write_uid", "share_token", "author_id", "is_published"]);
            const newItem = {
                ...rec,
                parent_id: rec.parent_id ? rec.parent_id[0] : null,
                tag_ids_raw: rec.tag_ids,
                tag_ids: (rec.tag_ids || []).map(id => this.tagIdToName.get(id) || ""),
                expanded: true,
            };
            this.allArticles.push(newItem);
            this.filterArticles();
            this.renderArticle(newItem);
            this._showToast(`Article: ${title} created successfully.`);
        } finally {
            this.state.creatingArticle = false;
            this.state.showNewArticlePanel = false;
            this.state.newArticleTitle = "";
        }
    }

    async createQuickArticleInSection(isPublished, parentId = null) {
        if (this.state.creatingArticle) return;
        const title = "Sin título";
        this.state.creatingArticle = true;
        try {
            const [newId] = await this.orm.create("knowledge.article", [{
                name: title,
                parent_id: parentId,
                is_published: isPublished,
                active: true,
            }]);
            const [rec] = await this.orm.read("knowledge.article", [newId],
                ["id", "name", "parent_id", "tag_ids", "active", "display_name", "views_count", "likes_count", "liked_by_ids", "create_date", "write_date", "create_uid", "write_uid", "share_token", "author_id", "is_published"]);
            const newItem = {
                ...rec,
                parent_id: rec.parent_id ? rec.parent_id[0] : null,
                tag_ids_raw: rec.tag_ids,
                tag_ids: (rec.tag_ids || []).map(id => this.tagIdToName.get(id) || ""),
                expanded: true,
            };
            this.allArticles.push(newItem);

            // If it's a child, make sure parent is expanded
            if (parentId) {
                const parent = this.allArticles.find(a => a.id === parentId);
                if (parent) parent.expanded = true;
            }

            this.filterArticles();
            await this.renderArticle(newItem);
            this._showToast(`Nuevo artículo "${title}" creado.`);
        } finally {
            this.state.creatingArticle = false;
        }
    }

    async toggleLike() {
        const articleId = this.state.currentArticleId;
        if (!articleId) return;
        try {
            const res = await this.orm.call("knowledge.article", "action_toggle_like", [articleId]);
            this.state.likedByIds = res.liked_by_ids || [];
            this.state.likesCount = res.likes_count || 0;
            if (this.state.currentArticle?.id === articleId) {
                this.state.currentArticle.liked_by_ids = this.state.likedByIds;
                this.state.currentArticle.likes_count = this.state.likesCount;
            }
            ;
        } catch (e) {
            console.error("toggleLike failed", e);
            this._showToast("Could not update like.", "error");
        }
    }

    expandAll() {
        this.articles.forEach(a => a.expanded = true);
        localStorage.setItem("expanded_nodes", JSON.stringify(
            this.articles.filter(a => a.expanded).map(a => a.id)
        ));
        this._refreshTree(this.isFilteredView);
    }

    collapseAll() {
        this.articles.forEach(a => a.expanded = false);
        localStorage.setItem("expanded_nodes", JSON.stringify(
            this.articles.filter(a => a.expanded).map(a => a.id)
        ));
        this._refreshTree(this.isFilteredView);
    }

    onSortChange(ev) {
        this.state.sortOrder = ev.target.value;
        localStorage.setItem("article_sort_order", this.state.sortOrder);
        this.sortArticles();
        this._refreshTree(this.isFilteredView);
    }

    sortArticles() {
        const key = this.state.sortOrder;
        const getTime = s => new Date(s).getTime();

        const comparator = {
            name: (a, b) => a.name.localeCompare(b.name),
            name_desc: (a, b) => b.name.localeCompare(a.name),
            created: (a, b) => getTime(a.create_date) - getTime(b.create_date),
            created_desc: (a, b) => getTime(b.create_date) - getTime(a.create_date),
            updated_desc: (a, b) => getTime(b.write_date) - getTime(a.write_date),
            likes_desc: (a, b) => (b.likes_count || 0) - (a.likes_count || 0),
            views_desc: (a, b) => (b.views_count || 0) - (a.views_count || 0),
        }[key];

        if (comparator) {
            this.articles.sort(comparator);
        }
    }

    sortFilteredArticles() {
        const key = this.state.sortOrder;
        const getTime = s => new Date(s).getTime();

        const comparator = {
            name: (a, b) => a.name.localeCompare(b.name),
            name_desc: (a, b) => b.name.localeCompare(a.name),
            created: (a, b) => getTime(a.create_date) - getTime(b.create_date),
            created_desc: (a, b) => getTime(b.create_date) - getTime(a.create_date),
            updated_desc: (a, b) => getTime(b.write_date) - getTime(a.write_date),
            likes_desc: (a, b) => (b.likes_count || 0) - (a.likes_count || 0),
            views_desc: (a, b) => (b.views_count || 0) - (a.views_count || 0),
        }[key];

        if (comparator) {
            this.filteredArticles.sort(comparator);
        }
    }

    _restorePersistedState() {
        const rawTags = JSON.parse(localStorage.getItem("selected_tags") || "[]");
        this.state.selectedTags = rawTags.map(id => parseInt(id));
        this.state.onlyFavorites = localStorage.getItem("only_favorites") === "1";
        this.state.showArchived = localStorage.getItem("show_archived") === "1";
        this.state.sortOrder = localStorage.getItem("article_sort_order") || "name";
        this.lastSelectedArticleId = parseInt(localStorage.getItem("last_article_id")) || null;
        const expandedIds = JSON.parse(localStorage.getItem("expanded_nodes") || "[]");
        this.expandedSet = new Set(expandedIds);

        this.state.sidebarCollapsed = localStorage.getItem("sidebar_collapsed") === "1";
    }

    _updateUrlParam(hash, key, value) {
        const [basePath, paramStr] = hash.replace(/^#/, '').split('?');
        const params = new URLSearchParams(paramStr || '');
        params.set(key, value);
        return `#${basePath}?${params.toString()}`;
    }

    async _getPartnerId() {
        const [user] = await this.orm.read("res.users", [this.user.userId], ["partner_id"]);
        return user.partner_id?.[0];
    }

    toggleSearchInContent() {
        this.state.searchInContent = !this.state.searchInContent;
        localStorage.setItem("search_in_content", this.state.searchInContent ? "1" : "0");
        this._performSearch();
    }

    toggleSidebar() {
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
        localStorage.setItem("sidebar_collapsed", this.state.sidebarCollapsed ? "1" : "0");

        const rootEl = this.root.el;
        const sidebar = rootEl.querySelector(".o_knowledge_sidebar");

        if (this.state.sidebarCollapsed) {
            rootEl.classList.add("sidebar-collapsed");
        } else {
            rootEl.classList.remove("sidebar-collapsed");
            const savedWidth = parseInt(localStorage.getItem("sidebar_width"), 10);
            sidebar.style.width = (!isNaN(savedWidth) ? savedWidth : 280) + "px";
        }
    }

    _initStickyToolbar() {
        const scroller = this.root.el.querySelector(".o_knowledge_content");
        const header = this.root.el.querySelector(".o_article_toolbar");
        if (!scroller || !header) return;

        const onScroll = () => header.classList.toggle("is-stuck", scroller.scrollTop > 0);
        scroller.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
    }

    toggleCardPanel() {
        if (this.state.showCardPanel) {
            this._closeCardPanel();
        } else {
            this._openCardPanel();
        }
    }

    _openCardPanel() {
        this.state.showCardPanel = true;
        setTimeout(() => this._positionCardPanel(), 0);

        this._boundReposition = this._boundReposition || this._positionCardPanel.bind(this);
        window.addEventListener("scroll", this._boundReposition, true);
        window.addEventListener("resize", this._boundReposition);
    }

    _closeCardPanel() {
        this.state.showCardPanel = false;
        if (this._boundReposition) {
            window.removeEventListener("scroll", this._boundReposition, true);
            window.removeEventListener("resize", this._boundReposition);
        }
    }

    _positionCardPanel() {
        const toggle = this.cardToggleIcon?.el;
        const panel = this.cardPanel?.el;
        if (!toggle || !panel) return;

        const t = toggle.getBoundingClientRect();
        const prevVis = panel.style.visibility;
        const prevDisp = panel.style.display;
        panel.style.visibility = "hidden";
        panel.style.display = "block";
        const pw = panel.offsetWidth || 256;
        panel.style.visibility = prevVis || "";
        panel.style.display = prevDisp || "";

        const gap = 8;
        let top = t.bottom + gap;
        let left = t.right - pw;

        const vw = window.innerWidth, vh = window.innerHeight;
        left = Math.max(8, Math.min(left, vw - pw - 8));
        const ph = panel.offsetHeight || 300;
        if (top + ph > vh - 8) top = Math.max(8, vh - ph - 8);

        Object.assign(panel.style, {
            position: "fixed",
            top: `${top}px`,
            left: `${left}px`,
            right: "auto",
            bottom: "auto",
        });
    }

    // --- Cover Image Methods (Auto-bind as arrow functions for safety) ---

    openIconPicker = (ev) => {
        let target = ev?.currentTarget;

        // If coming from the options menu, anchor to the main content area for better UX
        if (!target || target.classList.contains('o_card_action')) {
            target = this.root.el.querySelector(".o_article_main_icon") ||
                this.root.el.querySelector(".o_article_display h1") ||
                this.root.el.querySelector(".o_article_display");
        }

        this.popover.open(target, {
            position: 'top',
            onSelect: (codepoints) => {
                this.updateIcon(codepoints);
                this.popover.close();
            }
        });
    }

    updateIcon = async (icon) => {
        if (!this.state.currentArticle) return;
        const articleId = this.state.currentArticleId;
        try {
            await this.orm.write("knowledge.article", [articleId], { icon: icon });

            // Update reactive state
            this.state.currentArticle.icon = icon;

            // Sync with master list
            const masterArticle = this.allArticles.find(a => a.id === articleId);
            if (masterArticle) masterArticle.icon = icon;

            // Update content cache
            const cached = this.articleContentCache.get(articleId);
            if (cached) {
                cached.icon = icon;
                this.articleContentCache.set(articleId, cached);
            }

            this._refreshTree(this.isFilteredView);
            this._showToast("Icono actualizado.");
        } catch (err) {
            this._showToast("Error al actualizar el icono.", "danger");
        }
    }

    removeIcon = async () => {
        if (!this.state.currentArticle) return;
        const articleId = this.state.currentArticleId;
        try {
            await this.orm.write("knowledge.article", [articleId], { icon: false });
            this.state.currentArticle.icon = false;
            const masterArticle = this.allArticles.find(a => a.id === articleId);
            if (masterArticle) masterArticle.icon = false;
            this._refreshTree(this.isFilteredView);
            this._showToast("Icono eliminado.");
        } catch (err) {
            this._showToast("Error al eliminar el icono.", "danger");
        }
    }

    openCoverModal = () => {
        this.state.showCoverModal = true;
    }

    closeCoverModal = () => {
        this.state.showCoverModal = false;
    }

    updateCover = async (type, value, extra = {}) => {
        if (!this.state.currentArticle) return;
        const articleId = this.state.currentArticleId;
        const vals = { ...extra, cover_image_type: type };
        if (type === 'url') vals.cover_image_url = value;
        if (type === 'binary') vals.cover_image_binary = value;

        try {
            await this.orm.write("knowledge.article", [articleId], vals);

            // Update the reactive state (currentArticle is a proxy)
            Object.assign(this.state.currentArticle, vals);

            // Sync with the master list (allArticles)
            const masterArticle = this.allArticles.find(a => a.id === articleId);
            if (masterArticle) {
                Object.assign(masterArticle, vals);
            }

            // Sync the content cache so it doesn't revert to old data on re-render
            const cached = this.articleContentCache.get(articleId);
            if (cached) {
                Object.assign(cached, vals);
                this.articleContentCache.set(articleId, cached);
            }

            this.closeCoverModal();
            this._showToast("Portada actualizada.");
        } catch (err) {
            this._showToast("Error al actualizar la portada.", "danger");
        }
    }

    onCoverUpload = (ev) => {
        const file = ev.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64 = e.target.result.split(',')[1];
            await this.updateCover('binary', base64);
        };
        reader.readAsDataURL(file);
    }

    addCover = async () => {
        const defaultCover = "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=2071&auto=format&fit=crop";
        await this.updateCover('url', defaultCover, { cover_position: 50 });
    }

    removeCover = async () => {
        await this.updateCover('none', '');
    }

    toggleReposition = () => {
        if (!this.state.isRepositioning) {
            this.state.originalCoverPos = this.state.currentArticle.cover_position || 0;
            this.state.isRepositioning = true;
        } else {
            this.state.isRepositioning = false;
        }
    }

    cancelReposition = () => {
        if (this.state.originalCoverPos !== undefined) {
            this.state.currentArticle.cover_position = this.state.originalCoverPos;
        }
        this.state.isRepositioning = false;
    }

    saveCoverPosition = async (val) => {
        const position = parseInt(val);
        const type = this.state.currentArticle.cover_image_type;
        const value = type === 'binary'
            ? this.state.currentArticle.cover_image_binary
            : (this.state.currentArticle.cover_image_url || '');

        await this.updateCover(type, value, { cover_position: position });
        this.state.isRepositioning = false; // Exit reposition mode
        this._showToast("Posición guardada.");
    }

    // --- Drag Repositioning Logic ---
    startDrag = (ev) => {
        if (!this.state.isRepositioning) return;
        ev.preventDefault(); // Prevent text selection
        this.state.isDragging = true;
        this.state.dragStartY = ev.clientY;
        this.state.dragStartPos = parseInt(this.state.currentArticle.cover_position || 50);
    }

    onDrag = (ev) => {
        if (!this.state.isDragging) return;
        ev.preventDefault();

        const deltaY = ev.clientY - this.state.dragStartY;
        // Sensitivity: 1px movement = 0.5% position change
        // Moving mouse UP (negative delta) -> Should show lower part of image -> Increase %
        const change = -deltaY * 0.5;

        let newPos = this.state.dragStartPos + change;

        // Clamp between 0 and 100
        if (newPos < 0) newPos = 0;
        if (newPos > 100) newPos = 100;

        this.state.currentArticle.cover_position = Math.round(newPos);
    }

    stopDrag = async () => {
        if (!this.state.isDragging) return;
        this.state.isDragging = false;
        // We do NOT auto-save here to let user adjust freely. 
        // They must click "Guardar posición" to commit to DB.
    }
}

function getTimeAgo(dateStr) {
    const now = new Date();
    const date = new Date(dateStr + 'Z');
    const seconds = Math.floor((now - date) / 1000);

    const intervals = [
        { label: 'year', seconds: 31536000 },
        { label: 'month', seconds: 2592000 },
        { label: 'day', seconds: 86400 },
        { label: 'hour', seconds: 3600 },
        { label: 'minute', seconds: 60 },
        { label: 'second', seconds: 1 },
    ];

    for (const interval of intervals) {
        const count = Math.floor(seconds / interval.seconds);
        if (count >= 1) {
            return `${count} ${interval.label}${count !== 1 ? 's' : ''} ago`;
        }
    }
    return 'just now';
}

function toTextAsync(html, cb) {
    const run = () => {
        const doc = new DOMParser().parseFromString(html || "", "text/html");
        cb((doc.body?.textContent || "").toLowerCase());
    };

    const ric = window.requestIdleCallback;
    if (typeof ric === "function") {
        ric(run, { timeout: 300 });
    } else {
        setTimeout(run, 0);
    }
}

registry.category("actions").add("knowledge_split_client", KnowledgeSplit);
