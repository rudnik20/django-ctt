=============
Getting started with django-ctt
=============

What it Django-ctt?
===========

Django-ctt is Django app, which help you store hierarchical data in database.
This is very simple, friendly and reusable app.

Installation
========

To install django-ctt clone repository:

https://github.com/HiddenData/django-ctt.git

Next run:

.. code-block:: console

    python setup.py install

Usage
=====

In your models.py file put:

.. code-block:: python

    import ctt
    from ctt.models import CTTModel

You must register your model (models.py):

.. code-block:: python

    ctt.register(your_model_name)

Finally run python manage.py syncdb to create necessary tables.

Now you have extra methods in your model objects e.g. `get_children()` and `get_ancestors()`.
Your register model has 2 extra fields: parent and level.

Example
~~~~~~

.. code-block:: python

    class Node(CTTModel):
        name = models.CharField(max_length=255)

    node = Node.objects.filter(id=1)
    print(node.get_children())
