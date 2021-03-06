#!/usr/bin/env python
#-*- coding: utf-8 -*-
#vim: set ts=4 sw=4 et fdm=marker : */

"""
Closure Tables Tree models.
"""
from django.db import models
from django.db.models import F
from django.db.models.query_utils import Q
from ctt.decorators import filtered_qs
from django.utils.translation import ugettext as _


class CTTModel(models.Model):
    """This class provide create tree from your model objects
    You must inherit this and register your subclass to use it:
    ctt.register(your_model_name)
    """
    parent = models.ForeignKey('self', null=True, blank=True)
    level = models.IntegerField(default=0, blank=True)
    _tpm = None # overwrite by core.register()
    tpd = None # overwrite by core.register()
    tpa = None # overwrite by core.register()
    _cls = None

    class Meta:
        abstract = True

    class CTTMeta:
        parent_field = 'parent'

    def __unicode__(self):
        if hasattr(self, 'name'):
            return self.name
        return unicode(self.id)

    def save(self, force_insert=False, force_update=False, using=None):
        """Save data to database

        :return: None
        """
        is_new = self.pk is None
        if not is_new:
            old_parent = self._cls.objects.get(pk=self.pk).parent
        else:
            old_parent = None
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 0
        super(CTTModel, self).save(force_insert, force_update, using)
        if is_new:
            self.insert_at(self.parent, save=False, allow_existing_pk=True)
        elif not self.parent and not old_parent:
            pass
        elif not self.parent or not old_parent:
            self.move_to(self.parent)
        elif old_parent.pk != self.parent.pk:
            self.move_to(self.parent)

    def get_ancestors(self, ascending=False, include_self=False):
        """Return node ancestors

        :param ascending: enable reverse order_by
        :param include_self: if true, put node to his ancestors
        :return: QuerySet of nodes
        """

        ancestors = self._cls.objects.filter(tpa__descendant_id=self.id)
        if not include_self:
            ancestors = ancestors.exclude(id=self.id)
        if ascending:
            ancestors = ancestors.order_by('tpa__path_len')
        else:
            ancestors = ancestors.order_by('-tpa__path_len')
        return ancestors

    @filtered_qs
    def get_children(self):
        """ Return node children

        :return: QuerySet of nodes
        """
        nodes = self._cls.objects.filter(
            Q(tpd__ancestor_id=self.id) & Q(tpd__path_len=1)
        )
        return nodes

    def get_descendant_count(self):
        """ Return number of descendants

        :return: integer
        """
        return self.get_descendants().count()

    def get_descendants(self, include_self=False):
        """ Return node descendants

        :param include_self: if true, put node to his descendants
        :return: QuerySet of nodes
        """
        nodes = self._cls.objects.filter(tpd__ancestor_id=self.id)
        if not include_self:
            nodes = nodes.exclude(id=self.id)
        return nodes

    def get_leafnodes(self, include_self=False):
        """ Return all leafs, which are descendants of node

        :param include_self: if true, return node if is leaf
        :return: QuerySet of nodes
        """
        nodes = self.get_descendants(include_self=include_self)
        nodes = nodes.exclude(tpa__path_len__gt=0)
        return nodes

    def get_level(self):
        """ Return tree level

        :return: integer
        """
        return self.level

    def _get_next_from_qs(self, qs):
        """ Return object after self in qs

        :param qs: QuerySet of Nodes
        :return: node object or None
        """
        take = False
        for item in qs:
            if take:
                return item
            if item == self:
                take = True
        return None

    def get_next_sibling(self, **filters):
        """ Return next sibling
        If you want have correct order, you have to use CTTOrderableModel!

        :param filters: extra query parameters
        :return: node object
        """
        siblings = self.get_siblings(include_self=True).filter(**filters)
        return self._get_next_from_qs(siblings)

    def get_previous_sibling(self, **filters):
        """ Return previous sibling
        If you want have correct order, you have to use CTTOrderableModel!

        :param filters: extra query parameters
        :return: node object
        """
        siblings = self.get_siblings(include_self=True).filter(**filters)
        return self._get_next_from_qs(siblings.reverse())

    def get_siblings(self, include_self=False):
        """ Return node siblings

        :param include_self: if true, put node to his siblings
        :return: QuerySet of Nodes
        """
        if not self.parent:
            nodes = self._cls.objects.filter(id=self.id)
        else:
            nodes = self._cls.objects.filter(
                Q(tpd__ancestor_id=self.parent_id) & Q(tpd__path_len=1)
            )
        if not include_self:
            nodes = nodes.exclude(id=self.id)
        return nodes

    def get_root(self):
        """ Return root of tree

        :return: node object
        """
        return self.tpd.latest('path_len').ancestor

    def insert_at(self, target, position='first-child', save=False,
                  allow_existing_pk=False):
        """ Insert node at target
        manager.insert_node

        :param target: node which will become parent for this node
        :param position: which child position
        :param save: if true, changes are save
        :param allow_existing_pk: this allow to use existing primary key
        :return: None
        """
        if not self.pk:
            self.save()
            return

        if self.pk and not allow_existing_pk and\
           self._cls.objects.filter(pk=self.pk).exists():
            raise ValueError(
                _('Cannot insert a node which has already been saved.'))

        if target:
            self.parent = target
            path = target.get_ancestors(ascending=True,
                include_self=True).only('id')
        else:
            path = []
        tree_paths = [self._tpm(ancestor_id=self.id, descendant_id=self.id,
            path_len=0), ]
        path_len = 1
        for node in path:
            tree_paths.append(
                self._tpm(ancestor_id=node.id, descendant_id=self.id,
                    path_len=path_len)
            )
            path_len += 1
        self._tpm.objects.bulk_create(tree_paths)

        if save:
            self.save()

    def is_ancestor_of(self, other, include_self=False):
        """Check is node ancestor of other node

        :param other: supposed descendant
        :return: True or False
        """
        nodes = other.get_ancestors(include_self=include_self)
        return self in nodes

    def is_child_node(self):
        """ Check is node child of other node

        :return: True or False
        """
        return not self.is_root_node()

    def is_descendant_of(self, other, include_self=False):
        """ Check is node descendant of other node

        :param other: supposed ancestor
        :param include_self:
        :return: True or False
        """
        nodes = other.get_descendants(include_self=include_self)
        return self in nodes

    def is_leaf_node(self):
        """Return True if node is leaf

        :return: True or False
        """
        return self._cls.objects.filter(
            tpd__ancestor_id=self.id).count() == 1

    def is_root_node(self):
        """Return True if node is root

        :return: True or False
        """
        return self.level == 0

    def _get_unique_ancestors(self, target, others=False, include_self=False,
                              include_target=False):
        """
            1
           / \
          2   5
         / \   \
        3   4   6

        3._get_unique_ancestors(6) = 2
        3._get_unique_ancestors(6, True) = 5

        include_target works only with others=True
        include_self works only with others=False

        Return node ancestors unique compare with target ancestors.
        If others == True return target ancestors unique compare with node
        ancestors

        :param others: if True return target ancestors instead node ancestors
        :return: QuerySet of Nodes
        """
        #    ancestors = self._cls.objects.filter(tpa__descendant_id=self.id)
        if others:
            uni_ancestors = self._cls.objects.filter(
                Q(tpa__descendant_id=target.id)
                &
                ~Q(tpa__descendant_id=self.id)
            )
        else:
            uni_ancestors = self._cls.objects.filter(
                Q(tpa__descendant_id=self.id)
                &
                ~Q(tpa__descendant_id=target.id)
            )
        if not include_self:
            uni_ancestors = uni_ancestors.exclude(id=self.id)
        if not include_target:
            uni_ancestors = uni_ancestors.exclude(id=target.id)
        return uni_ancestors

    def move_to(self, target, position='first-child'):
        """ Move node to target, target become parent of moved node.

        :param target: node which will become parent for this node
        :return: None
        """
        if self in target.get_ancestors(include_self=True):
            raise ValueError(_('Cannot move node to its descendant or itself.'))

        old_parent = self._cls.objects.get(pk=self.pk).parent
        if old_parent is target:
            return

        self.tpd.all().delete()
        self.insert_at(target, save=True, allow_existing_pk=True)

        descendants = self.get_descendants()
        for node in descendants:
            node.tpd.all().delete()
            node.insert_at(node.parent, save=False, allow_existing_pk=True)

    @classmethod
    def _rebuild_tree(cls):
        """
        little clever but certain :)

        :return: None
        """
        cls._tpm.objects.all().delete()
        for node in cls._cls.objects.all().order_by('level'):
            node.insert_at(node.parent, allow_existing_pk=True)

    @classmethod
    def _rebuild_qs(cls, qs):
        """
        Rebuid all paths cross qs, very slow, use _rebuild_tree only if you
        know what do you do

        :param qs: QuerySet of Nodes
        :return: None
        """

        def item_descendants(item, result=None):
            if not result:
                result = []

            children = list(cls._cls.objects.filter(parent=item))
            result.extend(children)
            for c in children:
                item_descendants(c, result)

            return result

        def item_ancestors(item, result=None):
            if not result:
                result = []

            while item:
                result.append(item)
                item = item.parent

            return result

        related_nodes = set()
        for item in qs:
            # Get parents:
            related_nodes = related_nodes.union(item_ancestors(item))
            related_nodes = related_nodes.union(item_descendants(item))

        tpms = cls._tpm.objects.filter(
            ancestor__in=related_nodes,
            descendant__in=related_nodes)

        tpms.delete()

        for node in sorted(related_nodes, key=lambda i: i.level):
            node.insert_at(node.parent, allow_existing_pk=True)


class CTTOrderableModel(CTTModel):
    """This is subclass of CTTModel which keep correct elements order
    You must inherit this and register your subclass to use it:
    ctt.register(your_model_name)
    """
    order = models.IntegerField(verbose_name=_(u"order"))
    _interval = 10

    class Meta:
        abstract = True
        ordering = ('order',)

    def get_next_sibling(self, **filters):
        """ Return next sibling of node

        :param filters: extra query parameters
        :return: node object or None
        """
        siblings = self.get_siblings().filter(**filters)
        ret_node = siblings.filter(order__gt=self.order)
        if not ret_node:
            return None
        return ret_node[0]

    def get_previous_sibling(self, **filters):
        """Return previous sibling of node

        :param filters: extra query parameters
        :return: node object or None
        """
        siblings = self.get_siblings().filter(**filters)
        ret_node = siblings.filter(order__lt=self.order).reverse()
        if not ret_node:
            return None
        return ret_node[0]

    def get_children(self):
        """ Return node children

        :return: node object
        """
        return super(CTTOrderableModel, self).get_children().order_by('order')

    def get_siblings(self, include_self=False):
        """Return node siblings

        :return: node object
        """
        return super(CTTOrderableModel, self).get_siblings(
            include_self).order_by('order')

    def save(self, force_insert=False, force_update=False, using=None):
        """Save data to database

        :return: None
        """
        self._fix_order()
        super(CTTOrderableModel, self).save(force_insert, force_update, using)

    def _push_forward(self, from_pos):
        """ Push forward node from position

        :param from_pos: position from push
        :return: None
        """
        new_order = from_pos + self._interval
        siblings = self.get_siblings()
        to_push = siblings.filter(order__gt=self.order, order__lte=new_order).\
        order_by('order')
        if to_push.exists():
            to_push[0]._push_forward(new_order)

        self.order = new_order
        self.save()

    def move_before(self, sibling):
        """ Move before sibling

        :param sibling: node which is sibling for self
        :return: None
        """
        before = self.get_siblings().filter(order__lt=sibling.order).\
        order_by('-order')
        if before.exists():
            self.order = before[0].order + 1
        else:
            self.order = sibling.order - self._interval

    def move_after(self, sibling):
        """Move after sibling

        :param sibling: node which is sibling for self
        :return: None
        """
        self.order = sibling.order + 1

    def _fix_order(self):
        """ Add correct order to node

        :return: None
        """
        if not self.order:
            if self.get_siblings().exists():
                max_order_sibling = self.get_siblings().order_by('-order')[0]
                self.order = max_order_sibling.order + self._interval
            else:
                self.order = 0

        self._check_order_conflicts()

    def _check_order_conflicts(self):
        """ Find order conflicts and fix them

        :return: None
        """
        q = self.get_siblings()
        if self.pk:
            q = q.exclude(pk=self.pk)

        conflicts = q.filter(order=self.order)
        if conflicts.exists():
            candidates = q.filter(order__gte=self.order)
            candidates.update(order=F('order') + 1)
