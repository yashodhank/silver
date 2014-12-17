import datetime
from django_filters import FilterSet, CharFilter, BooleanFilter

from rest_framework import generics, permissions, status, filters
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import ListBulkCreateAPIView
from silver.api.dateutils import last_date_that_fits

from silver.models import (MeteredFeatureUnitsLog, Subscription, MeteredFeature,
                           Customer, Plan, Provider)
from silver.api.serializers import (MeteredFeatureUnitsLogSerializer,
                                    CustomerSerializer, SubscriptionSerializer,
                                    SubscriptionDetailSerializer,
                                    PlanSerializer, MeteredFeatureSerializer,
                                    ProviderSerializer)
from silver.utils import get_object_or_None


class PlanFilter(FilterSet):
    name = CharFilter(name='name', lookup_type='icontains')
    currency = CharFilter(name='currency', lookup_type='icontains')
    enabled = BooleanFilter(name='enabled', lookup_type='iexact')
    private = BooleanFilter(name='private', lookup_type='iexact')
    interval = CharFilter(name='interval', lookup_type='icontains')
    product_code = CharFilter(name='product_code', lookup_type='icontains')
    provider = CharFilter(name='provider__company', lookup_type='icontains')

    class Meta:
        model = Plan
        fields = ['name', 'currency', 'enabled', 'private', 'product_code',
                  'currency', 'provider', 'interval']


class PlanList(generics.ListCreateAPIView):
    """
    **Plans endpoint**
    """
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = PlanSerializer
    queryset = Plan.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PlanFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Plan.
        """
        return super(PlanList, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Plans.

        Filtering can be done with the following parameters: `name`, `enabled`,
        `currency`, `private`, `interval`, `product_code`, `provider`.
        """
        return super(PlanList, self).get(request, *args, **kwargs)


class PlanDetail(generics.RetrieveDestroyAPIView):
    """
    **Plan endpoint.**
    """
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = PlanSerializer
    model = Plan

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Plan, pk=pk)

    def get(self, request, *args, **kwargs):
        """
        Returns a specific Plan.
        """
        return super(PlanDetail, self).get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Updates the `name`, `generate_after` and `due_days` fields of a Plan.
        """
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        name = request.data.get('name', None)
        generate_after = request.data.get('generate_after', None)
        due_days = request.data.get('due_days', None)
        plan.name = name or plan.name
        plan.generate_after = generate_after or plan.generate_after
        plan.due_days = due_days or plan.due_days
        plan.save()
        return Response(PlanSerializer(plan, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        Performs a soft delete on a specific Plan.
        """
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        plan.enabled = False
        plan.save()
        return Response({"deleted": not plan.enabled},
                        status=status.HTTP_200_OK)


class PlanMeteredFeatures(generics.ListAPIView):
    """
    Returns a list of the plan's Metered Features.
    """
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_queryset(self):
        plan = get_object_or_None(Plan, pk=self.kwargs['pk'])
        return plan.metered_features.all() if plan else None


class MeteredFeaturesFilter(FilterSet):
    name = CharFilter(name='name', lookup_type='icontains')

    class Meta:
        model = MeteredFeature
        fields = ('name', )


class MeteredFeatureList(ListBulkCreateAPIView):
    """
    Metered Features endpoint.
    """
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    queryset = MeteredFeature.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = MeteredFeaturesFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Metered Feature.
        """
        return super(MeteredFeatureList, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Metered Features.

        Filtering can be done with the following parameter: `name`.
        """
        return super(MeteredFeatureList, self).get(request, *args, **kwargs)


class MeteredFeatureDetail(generics.RetrieveAPIView):
    """
    Returns a specific Metered Feature.
    """
    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(MeteredFeature, pk=pk)

    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature


class SubscriptionFilter(FilterSet):
    plan = CharFilter(name='plan__name', lookup_type='icontains')
    customer = CharFilter(name='customer__name', lookup_type='icontains')
    company = CharFilter(name='customer__company', lookup_type='icontains')

    class Meta:
        model = Subscription
        fields = ['plan', 'customer', 'company']


class SubscriptionList(generics.ListCreateAPIView):
    """
    **Subscriptions endpoint**
    """
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SubscriptionFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Subscription.
        """
        return super(SubscriptionList, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Subscriptions.

        Filtering can be done with the following parameters: `plan`,
        `customer`, `company`.
        """
        return super(SubscriptionList, self).get(request, *args, **kwargs)


class SubscriptionDetail(generics.RetrieveAPIView):
    """
    Returns a specific Subscription.
    """
    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Subscription, pk=pk)

    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    model = Subscription
    serializer_class = SubscriptionDetailSerializer


class SubscriptionDetailActivate(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        """
        Used to activate a specific Subscription.

        When activating a subscription the following happen:

        * the subscription `start_date` is set to the current date if it isn't
        already set or given in the request;
        * the subscription `trial_end_date` is computed from the `start_date`
        plus the plan's `trial_period_days` if it hasn't been already set or
        given in the request;
        * the subscription `state` is transitioned to `active`.

        This transition is only available from the `inactive` state.
        """
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        if sub.state != 'inactive':
            message = 'Cannot activate subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.POST.get('_content', None):
                start_date = request.data.get('start_date', None)
                trial_end = request.data.get('trial_end_date', None)
                sub.activate(start_date=start_date, trial_end_date=trial_end)
                sub.save()
            else:
                sub.activate()
                sub.save()
            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class SubscriptionDetailCancel(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        """
        Used to cancel a specific Subscription.

        A `when` parameter needs to be provided in the request body.
        It can take two values: `now` and `end_of_billing_cycle`.

        When cancelling a subscription `now`, a final invoice is issued and the
        subscription is transitioned to `ended` state.

        When cancelling a subscription at the `end_of_billing_cycle` the
        subscription is only transitioned to the `canceled` state.
        At the end of the billing cycle a final invoice will be issued and the
        subscription will be transitioned to the `ended` state.
        """
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        when = request.data.get('when', None)
        if sub.state != 'active':
            message = 'Cannot cancel subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if when == 'now':
                sub.cancel()
                sub.end()
                sub.save()
                return Response({"state": sub.state},
                                status=status.HTTP_200_OK)
            elif when == 'end_of_billing_cycle':
                sub.cancel()
                sub.save()
                return Response({"state": sub.state},
                                status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)


class SubscriptionDetailReactivate(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        """
        Used to reactivate a specific Subscription.

        Subscriptions which are canceled, can be reactivated before the end of
        the billing cycle.

        The request just transitions a subscription from `canceled` to `active`.
        """
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('sub', None))
        if sub.state != 'canceled':
            msg = 'Cannot reactivate subscription from %s state.' % sub.state
            return Response({"error": msg},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            sub.activate()
            sub.save()
            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class MeteredFeatureUnitsLogList(APIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    paginate_by = None

    def get(self, request, format=None, **kwargs):
        """
        Returns a Subscription's Metered Feature Units Log.

        The Units Log consists of multiple buckets representing billing cycles.
        """
        metered_feature_pk = kwargs.get('mf', None)
        subscription_pk = kwargs.get('sub', None)
        logs = MeteredFeatureUnitsLog.objects.filter(
            metered_feature=metered_feature_pk,
            subscription=subscription_pk)
        serializer = MeteredFeatureUnitsLogSerializer(
            logs, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        """
        Updates a Subscription's Metered Feature Units Log.

        In order to perform such an action the subscription must be active.

        There are 3 parameters required in the request body: `count`,
        `update_type` and `date`.

        The `count` parameter is the value to update the bucket with and it can
        be either positive or negative.

        The `update_type` parameter can be absolute (meaning the new bucket
        value will be equal to the count value) or relative (meaning the count
        value will be added to the bucket value).

        The bucket is determined using the `date` parameter.
        The buckets can be updated until the time given by the bucket
        `end_date` + the plan's `generate_after` seconds is older than the
        time when the request is made.
        After that, the buckets are frozen and cannot be updated anymore.

        Requests that are invalid or late will return a HTTP 4XX status code
        response.
        """
        metered_feature_pk = self.kwargs['mf']
        subscription_pk = self.kwargs['sub']
        date = request.data.get('date', None)
        consumed_units = request.data.get('count', None)
        update_type = request.data.get('update_type', None)
        if subscription_pk and metered_feature_pk:
            subscription = get_object_or_None(Subscription, pk=subscription_pk)
            metered_feature = get_object_or_None(MeteredFeature,
                                                 pk=metered_feature_pk)

            if subscription and metered_feature:
                if subscription.state != 'active':
                    return Response({"detail": "Subscription is not active"},
                                    status=status.HTTP_403_FORBIDDEN)
                if date and consumed_units is not None and update_type:
                    try:
                        date = datetime.datetime.strptime(date,
                                                          '%Y-%m-%d').date()
                        csd = subscription.current_start_date
                        ced = subscription.current_end_date

                        if date <= csd:
                            csdt = datetime.datetime.combine(csd, datetime.time())
                            allowed_time = datetime.timedelta(
                                seconds=subscription.plan.generate_after)
                            if datetime.datetime.now() < csdt + allowed_time:
                                ced = csd - datetime.timedelta(days=1)
                                csd = last_date_that_fits(
                                    initial_date=subscription.start_date,
                                    end_date=ced,
                                    interval_type=subscription.plan.interval,
                                    interval_count=subscription.plan.interval_count
                                )

                        if csd <= date <= ced:
                            if metered_feature not in \
                                    subscription.plan.metered_features.all():
                                err = "The metered feature does not belong to "\
                                      "the subscription's plan."
                                return Response(
                                    {"detail": err},
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            try:
                                log = MeteredFeatureUnitsLog.objects.get(
                                    start_date=csd,
                                    end_date=ced,
                                    metered_feature=metered_feature_pk,
                                    subscription=subscription_pk
                                )
                                if update_type == 'absolute':
                                    log.consumed_units = consumed_units
                                elif update_type == 'relative':
                                    log.consumed_units += consumed_units
                                log.save()
                            except MeteredFeatureUnitsLog.DoesNotExist:
                                log = MeteredFeatureUnitsLog.objects.create(
                                    metered_feature=metered_feature,
                                    subscription=subscription,
                                    start_date=subscription.current_start_date,
                                    end_date=subscription.current_end_date,
                                    consumed_units=consumed_units
                                )
                            finally:
                                return Response({"count": log.consumed_units},
                                                status=status.HTTP_200_OK)
                        else:
                            return Response({"detail": "Date is out of bounds"},
                                            status=status.HTTP_400_BAD_REQUEST)
                    except TypeError:
                        return Response({"detail": "Invalid date format"},
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"detail": "Not enough information provided"},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": "Not found"},
                                status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Wrong address"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerFilter(FilterSet):
    active = BooleanFilter(name='is_active', lookup_type='iexact')
    email = CharFilter(name='email', lookup_type='icontains')
    company = CharFilter(name='company', lookup_type='icontains')
    name = CharFilter(name='name', lookup_type='icontains')
    country = CharFilter(name='country', lookup_type='icontains')
    sales_tax_name = CharFilter(name='sales_tax_name', lookup_type='icontains')

    class Meta:
        model = Customer
        fields = ['email', 'name', 'company', 'active', 'country',
                  'sales_tax_name']


class CustomerList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = CustomerFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Customer.
        """
        return super(CustomerList, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Customers.

        Specifying the filtering parameter `overdue=true` will narrow the
        results to all the customers which have overdue invoices.

        The `overdue_by=X` parameter can be used to list all the customers
        which have overdue invoices for more than X days.

        Further filtering can be done by using the following parameters:
        `email`, `name`, `company`, `active`, `country`, `sales_tax_name`.
        """
        return super(CustomerList, self).get(request, *args, **kwargs)


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = CustomerSerializer
    model = Customer

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(Customer, pk=pk)

    def put(self, request, *args, **kwargs):
        """
        Adds or does a full update on a Customer.
        """
        return super(CustomerDetail, self).put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Partially updates an existing Customer.
        """
        return super(CustomerDetail, self).patch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a specific Customer.
        """
        return super(CustomerDetail, self).get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Performs a soft delete on a specific Customer.

        Deleting a customer automatically cancels that customer's subscriptions.
        """
        return super(CustomerDetail, self).delete(request, *args, **kwargs)


class ProviderFilter(FilterSet):
    email = CharFilter(name='email', lookup_type='icontains')
    company = CharFilter(name='company', lookup_type='icontains')

    class Meta:
        model = Provider
        fields = ['email', 'company']


class ProviderListBulkCreate(ListBulkCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ProviderFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Provider.
        """
        return super(ProviderListBulkCreate, self).post(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Providers.

        Filtering can be done with the following parameters: `email`, `company`.
        """
        return super(ProviderListBulkCreate, self).get(request, *args, **kwargs)


class ProviderRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()

    def put(self, request, *args, **kwargs):
        """
        Adds or does a full update on a Provider.
        """
        return super(ProviderRetrieveUpdateDestroy, self).put(
            request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Partially updates an existing Provider.
        """
        return super(ProviderRetrieveUpdateDestroy, self).patch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a specific Provider.
        """
        return super(ProviderRetrieveUpdateDestroy, self).get(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Performs a soft delete on a specific Provider.
        """
        return super(ProviderRetrieveUpdateDestroy, self).delete(
            request, *args, **kwargs)
