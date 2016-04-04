from plone.app.layout.navigation.interfaces import INavigationRoot
from zope.interface import alsoProvides

from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

class SetupEnglishView(BrowserView):

    def __init__(self, context, request):
        super(SetupEnglishView, self).__init__(context, request)

    def __call__(self):
        portal_catalog = getToolByName(self, 'portal_catalog');

        result = []

        for brain in portal_catalog(path={ "query": "/Sanford Guide Web Edition/en/" }):
            objPath = '/'.join( brain.getObject().getPhysicalPath() )
            filename = objPath.rsplit("/",1)[1]

            result.append( '\nSet language to \'en\' for:' + objPath )
            brain.getObject().setLanguage('en')

        if not result:
            return "Nothing done."
        else:
            result.insert(0, "Set language to EN for all content under the /en language folder."
                "'%s'" % self.context.getId())
            return '\n'.join(result)

