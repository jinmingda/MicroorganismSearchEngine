# -*- coding: utf-8 -*-
"""This module contains the controller classes of the application."""

# symbols which are imported by "from mse.controllers import *"
__all__ = ['Root']

# standard library imports
import os.path
# import logging

# log = logging.getLogger('mse.controllers')

# third-party imports
from cherrypy import request
from sqlobject import SQLObjectNotFound
from turbogears import controllers, expose, identity, redirect, visit, paginate
from turbogears import widgets, error_handler, validators, validate
from turbogears.toolbox.catwalk import CatWalk
import threading

# project specific imports
from mse.model import VisitIdentity
from async import *


# logging in after successfully registering a new user
def login_user(user):
    """Associate given user with current visit & identity."""
    visit_key = visit.current().key
    try:
        link = VisitIdentity.by_visit_key(visit_key)
    except SQLObjectNotFound:
        link = None

    if not link:
        link = VisitIdentity(visit_key=visit_key, user_id=user.id)
    else:
        link.user_id = user.user_id

    user_identity = identity.current_provider.load_identity(visit_key)
    identity.set_current_identity(user_identity)


# Customer Classes
class RegistrationFields(widgets.WidgetsList):
    userName = widgets.TextField(label="Username")
    password = widgets.PasswordField(label="Password")
    confirmPassword = widgets.PasswordField(label="Re-enter Password")
    displayName = widgets.TextField(label="Your Name")
    email = widgets.TextField(label="Email")
    securityQuestion = widgets.SingleSelectField(label="Security Question",
                                                 options=["What's your mother's maiden name?",
                                                          "What's your first pet's name?",
                                                          "What is the last name of your favorite teacher?"])
    securityAnswer = widgets.TextField(label="Security Answer")
    consent = widgets.CheckBox(label="Informed Consent")


class RegistrationFieldsSchema(validators.Schema):
    userName = validators.UnicodeString(max=16, not_empty=True, strip=True)
    password = validators.UnicodeString(min=5, max=40, not_empty=True, strip=True)
    confirmPassword = validators.UnicodeString(min=5, max=40, not_empty=True, strip=True)
    displayName = validators.UnicodeString(not_empty=True, strip=True)
    email = validators.Email(not_empty=True, strip=True)
    securityQuestion = validators.OneOf(["What's your mother's maiden name?",
                                         "What's your first pet's name?",
                                         "What is the last name of your favorite teacher?"])
    securityAnswer = validators.UnicodeString(not_empty=True, strip=True)
    consent = validators.NotEmpty()
    chained_validators = [validators.FieldsMatch('password', 'confirmPassword')]


class SearchFields(widgets.WidgetsList):
    title = widgets.TextField(label="Assignment Title")
    query = widgets.TextArea(label="Input Spectrum")
    maxMass = widgets.TextField(label="Max. Peptide Mass")
    minMass = widgets.TextField(label="Min. Peptide Mass")
    massTolerance = widgets.TextField(label="Mass Tolerance")
    specMode = widgets.SingleSelectField(label="Mode", options=["Positive", "Negative"],
                                         default="Positive")
    database = widgets.SingleSelectField(label="Databases",
                                         options=["Ribosomal Proteins in Bacteria: Unreviewed",
                                                  "Ribosomal Proteins in Bacteria: Reviewed"],
                                         default="Ribosomal Proteins in Bacteria: Reviewed")


class SearchFieldsSchema(validators.Schema):
    title = validators.UnicodeString(not_empty=True, strip=True)
    query = validators.UnicodeString(not_empty=True, strip=True)
    maxMass = validators.Number(not_empty=True, strip=True)
    minMass = validators.Number(not_empty=True, strip=True)
    massTolerance = validators.Number(not_empty=True, strip=True)
    specMode = validators.OneOf(["Positive", "Negative"])
    database = validators.OneOf(["Ribosomal Proteins in Bacteria: Unreviewed",
                                 "Ribosomal Proteins in Bacteria: Reviewed"])


registrationForm = widgets.TableForm(
    fields=RegistrationFields(),
    validator=RegistrationFieldsSchema(),
    action="signupsubmit",
    submit_text="Submit"
)

engineForm = widgets.TableForm(
    fields=SearchFields(),
    validator=SearchFieldsSchema(),
    action="searchsubmit",
    submit_text="Submit"
)


class Root(controllers.RootController):
    catwalk = CatWalk(model)
    catwalk = identity.SecureObject(catwalk, identity.in_group('admin'))

    @expose('mse.templates.index')
    def index(self):
        siteTitle = "Welcome to MSE"
        return dict(siteTitle=siteTitle)

    @expose('mse.templates.about')
    def about(self):
        siteTitle = "Introduction"
        directory = os.path.dirname(__file__)
        with open(directory+'/static/text/abstract.txt', 'r') as AbstractContent:
            abstract = AbstractContent.read().strip().split("\n\n")
        with open(directory+'/static/text/references.txt', 'r') as ReferenceContent:
            ref = ReferenceContent.read().strip().split("\n")
        return dict(siteTitle=siteTitle, abstract=abstract, ref=ref)

    @expose('mse.templates.contact')
    def contact(self):
        authors = [
            {"name": "Mingda Jin",
             "phone": "(123)456-789",
             "email": "mj568@georgetown.edu"
             },
            {"name": "Nathan J Edwards",
             "phone": "(123)456-789",
             "email": "nje5@georgetown.edu"
             }
        ]
        siteTitle = "Contact"
        return dict(contacts=authors, siteTitle=siteTitle)

    @expose('mse.templates.login')
    def login(self, forward_url=None, *args, **kw):
        """Show the login form or forward user to previously requested page."""

        if forward_url:
            if isinstance(forward_url, list):
                forward_url = forward_url.pop(0)
            else:
                del request.params['forward_url']

        new_visit = visit.current()
        if new_visit:
            new_visit = new_visit.is_new

        if (not new_visit and not identity.current.anonymous
                and identity.was_login_attempted()
                and not identity.get_identity_errors()):
            # Redirection
            redirect(forward_url or '/searchlist', kw)

        if identity.was_login_attempted():
            if new_visit:
                msg = _(u"Cannot log in because your browser "
                         "does not support session cookies.")
            else:
                msg = _(u"The credentials you supplied were not correct or "
                         "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg = _(u"You must provide your credentials before accessing "
                     "this resource.")
        else:
            #msg = _(u"Please log in.")
            msg = _(u"")
            if not forward_url:
                forward_url = request.headers.get('Referer', '/')

        # we do not set the response status here anymore since it
        # is now handled in the identity exception.
        return dict(logging_in=True, message=msg,
            forward_url=forward_url, previous_url=request.path_info,
            original_parameters=request.params)

    @expose()
    @identity.require(identity.not_anonymous())
    def logout(self):
        """Log out the current identity and redirect to start page."""
        identity.current.logout()
        redirect('/')

    @expose('mse.templates.signupForm')
    def signupform(self):
        siteTitle = "Sign up"
        return dict(siteTitle=siteTitle, form=registrationForm)

    @expose()
    @validate(form=registrationForm)
    @error_handler(signupform)
    def signupsubmit(self, **kw):
        # Create a user
        model.User(user_name=kw['userName'], password=kw['password'], email_address=kw['email'],
                   display_name=kw['displayName'], security_question=kw['securityQuestion'],
                   security_answer=kw['securityAnswer'])

        # Create a Group
        #model.Group(group_name=u'guest', display_name=u'Guest Users')
        #model.Group(group_name=u'admin', display_name=u'Admin Users')

        # Assign created user to a group
        group = model.Group.by_group_name(u'admin')
        model.User.by_user_name(kw['userName']).addGroup(group)

        # Login automatically after registration
        user = model.User.by_user_name(kw['userName'])
        login_user(user)
        redirect('/signupconfirmation')

    @expose('mse.templates.signupConfirmation')
    def signupconfirmation(self):
        siteTitle = "Welcome"
        return dict(siteTitle=siteTitle)

    @expose('mse.templates.searchForm')
    @identity.require(identity.not_anonymous())
    def searchform(self, **kw):
        siteTitle = "Start Your Search"
        u = identity.current.user
        previousSearches = u.searches[::-1][:5]
        return dict(siteTitle=siteTitle, form=engineForm, values=kw, searchHistory=previousSearches)

    @expose()
    @identity.require(identity.not_anonymous())
    @validate(form=engineForm)
    @error_handler(searchform)
    def searchsubmit(self, **kw):
        u = identity.current.user
        model.SearchList(title=kw['title'], min_mass=kw['minMass'], max_mass=kw['maxMass'],
                         query=kw['query'], mass_tolerance=kw['massTolerance'], spec_mode=kw['specMode'],
                         database=kw['database'], user=u)

        # Start the search thread immediately
        t = threading.Thread(target=MicroorganismIdentification)
        t.daemon = True
        t.start()

        redirect('/searchlist')

    @expose('mse.templates.searchList')
    @identity.require(identity.not_anonymous())
    @paginate('searchData', default_order="-created")
    def searchlist(self):
        u = identity.current.user
        userSearch = u.searches
        siteTitle = "Your Searches"
        return dict(siteTitle=siteTitle, searchData=userSearch)

    @expose()
    @identity.require(identity.not_anonymous())
    def searchdelete(self, **kw):
        #print searchID
        #print "@" * 100
        #model.SearchList.deleteBy(searchID)
        redirect('/searchlist')

    @expose('mse.templates.searchResult')
    @identity.require(identity.not_anonymous())
    @paginate('resultData', default_order="p_value")
    def searchresult(self, searchID):
        s = model.SearchList.get(searchID)
        r = s.results
        return dict(resultData=r)