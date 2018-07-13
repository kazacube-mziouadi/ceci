from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import openerp
import time, tempfile
import logging

logger = logging.getLogger(__name__)

class value_to_be_present_in_element(object):
    """ An expectation for checking if the given value is present in the
    specified element.
    locator, text
    """
    def __init__(self, locator, text_):
        self.locator = locator
        self.text = text_

    def __call__(self, driver):
        try :
            el = EC._find_element(driver, self.locator)
            if not isinstance(el, bool) and el is not None:
                return self.text in (el.get_attribute("value") or el.get_attribute("text"))
            else:
                return False
        except StaleElementReferenceException:
            return False

@given(u'I am on the login page@{rule_id}@')
def step_impl(context, rule_id):
    context.browser.get(context.config.userdata['base_url'])
    assert 'OpenERP' in context.browser.title

@when(u"I fill test_id '{test_id}' with '{value}'@{rule_id}@")
def step_impl(context, test_id, value, rule_id):
    els = context.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[test_id="{}"]'.format(test_id))))
    el = els[-1]
    if value == u'\x8203':
        value = ''
    for e in els:
        if e.is_displayed() and e.location['y'] > 0:
            el = e
            break
    try:
        
        el_id = el.get_attribute("id")
        label = context.browser.find_element_by_css_selector("label[for=%s]"%el_id)
        ActionChains(context.browser).move_to_element(label).perform()
        time.sleep(0.5)
        context.help_text = context.browser.find_element_by_css_selector(".tipsy-inner p").text
        context.label = context.browser.find_element_by_css_selector(".tipsy-inner div").text
        ActionChains(context.browser).move_by_offset(-1000, -1000).perform()
        time.sleep(0.1)
    except Exception:
        context.label = label.text.rstrip(' \t\n:') if 'label' in locals() else ""
    try:
        el.clear()
        el.send_keys(Keys.CONTROL + "a")
        el.send_keys(Keys.DELETE)
        el.send_keys(value)
    except Exception:
        pass
    
@when(u"I fill {name} with '{value}'@{rule_id}@")
def step_impl(context, name, value, rule_id):
    els = context.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input[name="' + name + '"]')))
    el = els[-1]
    for e in els:
        if e.is_displayed() and e.location['y'] > 0:
            el = e
            break
    try:
        el.send_keys(value)
    except:
        raise Error('Can\'t click')

@when(u"I select {name} with '{value}'@{rule_id}@")
def step_impl(context, name, value, rule_id):
    el = context.wait.until(EC.visibility_of_element_located((By.NAME, name)))
    select = Select(el)
    select.select_by_value(value)

@when(u'I click {tag} with text "{name}"@{rule_id}@')
def step_impl(context, name, tag, rule_id):
    for i in range(5):
        try:
            els = context.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//' + tag + '[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"),normalize-space("' + name.lower() + '"))]')))
            el = els[-1]
            for e in els:
                if e.is_displayed() and e.location['y'] > 0:
                    el = e
                    break
            el.click()
            return True
        except StaleElementReferenceException:
            pass
    raise Error('Can\'t click')

@when(u"I click test_id '{test_id}'@{rule_id}@")
def step_impl(context, test_id, rule_id):
    for i in range(5):
        try:
            els = context.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[test_id="{}"]'.format(test_id))))
            el = els[-1]
            for e in els:
                if e.is_displayed() and e.location['y'] > 0:
                    el = e
                    break
            context.label = e.text
            el.click()
            return True
        except StaleElementReferenceException:
            pass
    raise Error('Can\'t click')

@then(u'I should be connected with "{user}"@{rule_id}@')
def step_impl(context, user, rule_id):
    el = context.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "username")))
    assert user in el.text

@then(u'I should see "{text}" in "{element}"@{rule_id}@')
def step_impl(context, text, element, rule_id):
    el = context.wait.until(value_to_be_present_in_element((By.CSS_SELECTOR, '[test_id="' + element + '"]'), text))

@then(u'I should see "{text}"@{rule_id}@')
def step_impl(context, text, rule_id):
    el = context.wait.until(EC.visibility_of_element_located((By.XPATH, '//*[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), normalize-space("' + text.lower() + '"))]')))

@then(u'I should not see "{text}"@{rule_id}@')
def step_impl(context, text, rule_id):
    try:
        el = context.browser.find_element_by_xpath('//*[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), normalize-space("' + text + '"))]')
    except:
        pass
    if el and el.is_displayed():
        raise Exception(u'Bad text')

@then(u'save screenshot@{rule_id}@')
def step_impl(context, rule_id):
    path = tempfile.NamedTemporaryFile().name
    context.browser.save_screenshot(path)
    context.screenshot = path

@when(u'I wait {sec} seconds@{rule_id}@')
def step_impl(context, sec, rule_id):
    time.sleep(int(sec))
    
@then(u'save value of field \'{field}\' in "{variable}"@{rule_id}@')
def save_field_in_variable(context, field, variable, rule_id):
    env = openerp.http.request.env
    var_obj = env['test.variable']
    var = var_obj.search([('name', '=', variable)])
    els = context.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[test_id="{}"]'.format(field))))
    el = els[-1]
    for e in els:
        if e.is_displayed() and e.location['y'] > 0:
            el = e
            break
    value = el.get_attribute("value") or context.browser.execute_script("return arguments[0].innerText;", el)
    if len(var):
        var.write({
                   'value':value,
                   })
    else:
        var.create({
                    'name': variable,
                    'value': value,
                    })

@then(u'delete variable "{variable}"@{rule_id}@')
def delete_variable(context, variable, rule_id):
    env = openerp.http.request.env
    var_obj = env['test.variable']
    var_obj.search([('name', '=', variable)]).unlink()

@then(u'save "{value}" in "{variable}"@{rule_id}@')
def save_variable(context, value, variable, rule_id):
    env = openerp.http.request.env
    var_obj = env['test.variable']
    var = var_obj.search([('name', '=', variable)])
    if len(var):
        var.write({
                   'value':value,
                   })
    else:
        var.create({
                    'name': variable,
                    'value': value,
                    })

