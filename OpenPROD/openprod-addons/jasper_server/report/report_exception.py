# -*- coding: utf-8 -*-



class JasperException(Exception):
    """
    Redefine correctly exception
    """
    def __init__(self, title='Error', message='Empty message'):
        self.title = title
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.title, self.message)

    def __repr__(self):
        return self.__str__()


class AuthError(JasperException):
    pass


class EvalError(JasperException):
    pass

if __name__ == '__main__':
    try:
        # test str method
        try:
            raise JasperException('Error', 'Test JasperException')
        except JasperException, e:
            assert str(e) == 'Error: Test JasperException', 'Incorrect str()'
        # test title attribute
        try:
            raise JasperException('Error', 'Test JasperException')
        except JasperException, e:
            assert e.title == 'Error', 'Title must return "Error"'
        # test message attribute
        try:
            raise JasperException('Error', 'Test JasperException')
        except JasperException, e:
            assert e.message == 'Test JasperException', \
                'Message must return "Test JasperException"'

    except AssertionError, a:
        print 'Test failed: %s' % a
    finally:
        print 'Finished'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
