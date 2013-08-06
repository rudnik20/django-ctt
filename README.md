django-ctt
==========

Implementation of sql trees with Closure Table


[![Build Status](https://travis-ci.org/HiddenData/django-ctt.png?branch=master)](https://travis-ci.org/HiddenData/django-ctt)


## What it Django-ctt?

Django-ctt is Django app, which help you store hierarchical data in database.
This is very simple, friendly and reusable app.

## Installation

To install django-ctt clone repository:

`https://github.com/HiddenData/django-ctt.git`

Next run:

`python setup.py install`

##Usage

In your models.py file put:

`import ctt
from ctt.models import CTTModel`

Your model must inherit CTTModel.

You must register your model (models.py):

`ctt.register(your_model_name)`

Finally run `python manage.py syncdb` to create necessary tables.

Now you have extra methods in your model objects e.g. `get_children()` and `get_ancestors()`.
Your register model has 2 extra fields: parent and level.

###Example:

`
class Node(CTTModel):
    name = models.CharField(max_length=255)`

`
node = Node.objects.filter(id=1)
print(node.get_children())
`
