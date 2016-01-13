from plone.app.i18n.locales.browser.selector import LanguageSelector
from plone.app.layout.navigation.interfaces import INavigationRoot
from zope.component import getMultiAdapter

from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_chain
from Acquisition import aq_inner
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from ZTUtils import make_query

from Products.LinguaPlone.interfaces import ITranslatable


class TranslatableLanguageSelector(LanguageSelector):
    """Language selector for translatable content.
    """

    set_language = True

    def available(self):
        if self.tool is not None:
            selector = self.tool.showSelector()
            languages = len(self.tool.getSupportedLanguages()) > 1
            return selector and languages
        return False

    def _translations(self, missing):
        # Figure out the "closest" translation in the parent chain of the
        # context. We stop at both an INavigationRoot or an ISiteRoot to look
        # for translations. We do want to find something that is definitely
        # in the language the user asked for.
        context = aq_inner(self.context)
        translations = {}
        chain = aq_chain(context)
        first_pass = True
        _checkPermission = getSecurityManager().checkPermission
        for item in chain:
            if ISiteRoot.providedBy(item):
                # We have a site root, which works as a fallback
                has_view_permission = bool(_checkPermission('View', item))
                for c in missing:
                    translations[c] = (item, first_pass, has_view_permission)
                break

            translatable = ITranslatable(item, None)
            if translatable is None:
                continue

            item_trans = item.getTranslations(review_state=False)
            for code, trans in item_trans.items():
                code = str(code)
                if code not in translations:
                    # make a link to a translation only if the user
                    # has view permission
                    has_view_permission = bool(_checkPermission('View', trans))
                    if (not INavigationRoot.providedBy(item)
                            and not has_view_permission):
                        continue
                    # If we don't yet have a translation for this language
                    # add it and mark it as found
                    translations[code] = (trans, first_pass,
                            has_view_permission)
                    missing = missing - set((code, ))

            if len(missing) <= 0:
                # We have translations for all
                break
            if INavigationRoot.providedBy(item):
                # Don't break out of the navigation root jail
                has_view_permission = bool(_checkPermission('View', item))
                for c in missing:
                    translations[c] = (item, False, has_view_permission)
                break
            first_pass = False
        # return a dict of language code to tuple. the first tuple element is
        # the translated object, the second argument indicates wether the
        # translation is a direct translation of the context or something from
        # higher up the translation chain
        return translations

    def _findpath(self, path, path_info):
        # We need to find the actual translatable content object. As an
        # optimization we assume it is one of the last three path segments
        match = filter(None, path[-3:])
        current_path = filter(None, path_info.split('/'))
        append_path = []
        stop = False
        while current_path and not stop:
            check = current_path.pop()
            if check == 'VirtualHostRoot' or check.startswith('_vh_'):
                # Once we hit a VHM marker, we should stop
                break
            if check not in match:
                append_path.insert(0, check)
            else:
                stop = True
        if append_path:
            append_path.insert(0, '')
        return append_path

    def _formvariables(self, form):
        formvariables = {}
        for k, v in form.items():
            if isinstance(v, unicode):
                formvariables[k] = v.encode('utf-8')
            else:
                formvariables[k] = v
        return formvariables

    def languages(self):
        context = aq_inner(self.context)
        results = LanguageSelector.languages(self)
        supported_langs = [v['code'] for v in results]
        missing = set([str(c) for c in supported_langs])
        translations = self._translations(missing)
        # We want to preserve the current template / view as used for the
        # current object and also use it for the other languages
        append_path = self._findpath(context.getPhysicalPath(),
                                     self.request.get('PATH_INFO', ''))
        formvariables = self._formvariables(self.request.form)
        _checkPermission = getSecurityManager().checkPermission

        non_viewable = set()
        for data in results:
            code = str(data['code'])
            data['translated'] = code in translations.keys()
            set_language = '?set_language=%s' % code

            try:
                appendtourl = '/'.join(append_path)
                if self.set_language:
                    appendtourl += '?' + make_query(formvariables,
                                                    dict(set_language=code))
                elif formvariables:
                    appendtourl += '?' + make_query(formvariables)
            except UnicodeError:
                appendtourl = '/'.join(append_path)
                if self.set_language:
                    appendtourl += set_language

            # added by JR: determine if authenticated member is a valid translator for the language
            mt = getToolByName(context, "portal_membership")
            gt = getToolByName(context, 'portal_groups')
            groups = gt.getGroupsByUserId( mt.getAuthenticatedMember().getUserName() )
            group_ids = [group.getId() for group in groups]
            translator_group = 'Translators-'+code

            is_valid_translator_for_lang = translator_group in group_ids

            if data['translated']:
                trans, direct, has_view_permission = translations[code]

                # added by JR: also check translators to see languages pertinent to their translation task only
                if not has_view_permission or not is_valid_translator_for_lang:
                    # shortcut if the user cannot see the item
                    non_viewable.add((data['code']))
                    continue

                state = getMultiAdapter((trans, self.request),
                        name='plone_context_state')
                if direct:
                    data['url'] = state.canonical_object_url() + appendtourl
                else:
                    data['url'] = state.canonical_object_url() + set_language
            else:
                has_view_permission = bool(_checkPermission('View', context))
                # Ideally, we should also check the View permission of default
                # items of folderish objects.
                # However, this would be expensive at it would mean that the
                # default item should be loaded as well.
                #
                # IOW, it is a conscious decision to not take in account the
                # use case where a user has View permission a folder but not on
                # its default item.

                # added by JR: also check translators to see languages pertinent to their translation task only
                if not has_view_permission or not is_valid_translator_for_lang:
                    non_viewable.add((data['code']))
                    continue

                state = getMultiAdapter((context, self.request),
                        name='plone_context_state')
                try:
                    data['url'] = state.canonical_object_url() + appendtourl
                except AttributeError:
                    data['url'] = context.absolute_url() + appendtourl

        # filter out non-viewable items
        results = [r for r in results if r['code'] not in non_viewable]
        return results
