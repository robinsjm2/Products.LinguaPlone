from plone.browserlayer.utils import registered_layers
from zope.interface import implements
from Products.CMFCore.permissions import AddPortalContent, ModifyPortalContent,\
    DeleteObjects

# BBB Zope 2.12
try:
    from zope.browsermenu.menu import BrowserMenu
    from zope.browsermenu.menu import BrowserSubMenuItem # pragma: no cover
except ImportError: # pragma: no cover
    from zope.app.publisher.browser.menu import BrowserMenu
    from zope.app.publisher.browser.menu import BrowserSubMenuItem

from Products.CMFCore.utils import getToolByName

from Products.LinguaPlone import LinguaPloneMessageFactory as _
from Products.LinguaPlone.browser.interfaces import ITranslateMenu
from Products.LinguaPlone.browser.interfaces import ITranslateSubMenuItem
from Products.LinguaPlone.interfaces import ILinguaPloneProductLayer


class TranslateMenu(BrowserMenu):
    implements(ITranslateMenu)

    def getUntranslatedLanguages(self, context):
        if not context.Language():
            # neutral content must get a language assigned first
            return []

        return context.unrestrictedTraverse('@@getUntranslatedLanguages')()

    def getMenuItems(self, context, request):
        """Return menu item entries in a TAL-friendly form."""

        menu = []
        url = context.absolute_url()
        lt = getToolByName(context, "portal_languages")
        mt = getToolByName(context, "portal_membership")

        can_translate = mt.checkPermission(AddPortalContent,
                                           context.getParentNode())
        can_set_language = mt.checkPermission(ModifyPortalContent, context)
        can_delete = mt.checkPermission(DeleteObjects, context.getParentNode())

        if not (can_translate or can_set_language or can_delete):
            return []

        langs = self.getUntranslatedLanguages(context)
        if can_translate:
            showflags = lt.showFlags()
            langs = self.getUntranslatedLanguages(context)

            for (lang_id, lang_name) in langs:
                icon=showflags and lt.getFlagForLanguageCode(lang_id) or None
                item={
                    "title": lang_name,
                    "description": _(u"title_translate_into",
                                     default=u"Translate into ${lang_name}",
                                     mapping={"lang_name": lang_name}),
                    "action": url+"/@@translate?newlanguage=%s" % lang_id,
                    "selected": False,
                    "icon": icon,
                    "extra": {"id": "translate_into_%s" % lang_id,
                              "separator": None,
                              "class": ""},
                    "submenu": None,
                    "width": 14,
                    "height": 11,
                    }

                # added by JR to check translator group membership so that only members of appropriate group can translate language
                gt = getToolByName(context, 'portal_groups')
                groups = gt.getGroupsByUserId( mt.getAuthenticatedMember().getUserName() )
                group_ids = [group.getId() for group in groups]
                translator_group = 'Translators-'+lang_id

                is_valid_translator_for_lang = translator_group in group_ids

                if is_valid_translator_for_lang:
                    menu.append(item)

        if can_set_language or can_delete:
            menu.append({
                "title": _(u"label_manage_translations",
                           default=u"Manage translations..."),
                "description": u"",
                "action": url+"/manage_translations_form",
                "selected": False,
                "icon": None,
                "extra": {"id": "_manage_translations",
                          "separator": langs and "actionSeparator" or None,
                          "class": ""},
                "submenu": None,
                })

        return menu


class TranslateSubMenuItem(BrowserSubMenuItem):
    implements(ITranslateSubMenuItem)

    title = _(u"label_translate_menu", default=u"Translate into...")
    description = _(u"title_translate_menu",
            default="Manage translations for your content.")
    submenuId = "plone_contentmenu_translate"

    order = 5
    extra = {"id": "plone-contentmenu-translate"}

    @property
    def action(self):
        return self.context.absolute_url() + "/manage_translations_form"

    def available(self):
        if self.disabled():
            return False # pragma: no cover
        elif not ILinguaPloneProductLayer in registered_layers():
            return False
        else:
            context = self.context
            mt = getToolByName(context, "portal_membership")
            can_translate = mt.checkPermission(AddPortalContent,
                                               context.getParentNode())
            can_set_language = mt.checkPermission(ModifyPortalContent, context)
            can_delete = mt.checkPermission(DeleteObjects,
                                            context.getParentNode())
            return can_translate or can_set_language

    def disabled(self):
        return False

    def selected(self):
        return False
