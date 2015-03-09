import datetime

from django.http.response import Http404

from rest_framework import generics, permissions, status, filters
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from silver.api.dateutils import last_date_that_fits
from silver.api.filters import (MeteredFeaturesFilter, SubscriptionFilter,
                                CustomerFilter, ProviderFilter, PlanFilter,
                                InvoiceFilter, ProformaFilter)
from silver.models import (MeteredFeatureUnitsLog, Subscription, MeteredFeature,
                           Customer, Plan, Provider, Invoice, ProductCode,
                           DocumentEntry, Proforma)
from silver.api.serializers import (MFUnitsLogSerializer,
                                    CustomerSerializer, SubscriptionSerializer,
                                    SubscriptionDetailSerializer,
                                    PlanSerializer, MeteredFeatureSerializer,
                                    ProviderSerializer, InvoiceSerializer,
                                    ProductCodeSerializer, ProformaSerializer,
                                    DocumentEntrySerializer)
from silver.api.generics import (HPListAPIView, HPListCreateAPIView,
                                 HPListBulkCreateAPIView)
from silver.utils import get_object_or_None


class PlanList(HPListCreateAPIView):
    """
    **Plans endpoint**
    """
    permission_classes = (permissions.IsAuthenticated,)
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
    permission_classes = (permissions.IsAuthenticated,)
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
        Disables a specific Plan.
        """
        plan = get_object_or_404(Plan.objects, pk=self.kwargs.get('pk', None))
        plan.enabled = False
        plan.save()
        return Response({"deleted": not plan.enabled},
                        status=status.HTTP_200_OK)


class PlanMeteredFeatures(HPListAPIView):
    """
    Returns a list of the plan's Metered Features.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_queryset(self):
        plan = get_object_or_None(Plan, pk=self.kwargs['pk'])
        return plan.metered_features.all() if plan else None


class MeteredFeatureList(HPListCreateAPIView):
    """
    **Metered Features endpoint.**
    """
    permission_classes = (permissions.IsAuthenticated,)
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
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MeteredFeatureSerializer
    model = MeteredFeature

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(MeteredFeature, pk=pk)


class SubscriptionList(HPListCreateAPIView):
    """
    **Subscriptions endpoint**
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SubscriptionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = SubscriptionFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Subscription.
        """
        customer_pk = self.kwargs.get('customer_pk', None)
        url = reverse('customer-detail', kwargs={'pk': customer_pk},
                      request=request)
        request.data.update({'customer': url})

        return super(SubscriptionList, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Subscriptions.

        Filtering can be done with the following parameters: `plan`,
        `reference`, `state`.
        """
        return super(SubscriptionList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        customer_pk = self.kwargs.get('customer_pk', None)
        queryset = Subscription.objects.filter(customer__id=customer_pk)
        return queryset.order_by('start_date')


class SubscriptionDetail(generics.RetrieveAPIView):
    """
    Returns a specific Subscription.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SubscriptionDetailSerializer

    def get_object(self):
        customer_pk = self.kwargs.get('customer_pk', None)
        subscription_pk = self.kwargs.get('subscription_pk', None)
        return get_object_or_404(Subscription, customer__id=customer_pk,
                                 pk=subscription_pk)


class SubscriptionDetailActivate(APIView):
    permission_classes = (permissions.IsAuthenticated,)

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
                                pk=self.kwargs.get('subscription_pk', None))
        if sub.state != 'inactive':
            message = 'Cannot activate subscription from %s state.' % sub.state
            return Response({"error": message},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.POST.get('_content', None):
                start_date = request.data.get('start_date', None)
                trial_end = request.data.get('trial_end_date', None)
                if start_date:
                    try:
                        start_date = datetime.datetime.strptime(
                            start_date, '%Y-%m-%d').date()
                    except TypeError:
                        return Response(
                            {'detail': 'Invalid start_date date format. Please '
                                       'use the ISO 8601 date format.'},
                            status=status.HTTP_400_BAD_REQUEST)
                if trial_end:
                    try:
                        trial_end = datetime.datetime.strptime(
                            trial_end, '%Y-%m-%d').date()
                    except TypeError:
                        return Response(
                            {'detail': 'Invalid trial_end date format. Please '
                                       'use the ISO 8601 date format.'},
                            status=status.HTTP_400_BAD_REQUEST)
                sub.activate(start_date=start_date, trial_end_date=trial_end)
                sub.save()
            else:
                sub.activate()
                sub.save()
            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class SubscriptionDetailCancel(APIView):
    permission_classes = (permissions.IsAuthenticated,)

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
                                pk=self.kwargs.get('subscription_pk', None))
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
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Used to reactivate a specific Subscription.

        Subscriptions which are canceled, can be reactivated before the end of
        the billing cycle.

        The request just transitions a subscription from `canceled` to `active`.
        """
        sub = get_object_or_404(Subscription.objects,
                                pk=self.kwargs.get('subscription_pk', None))
        if sub.state != 'canceled':
            msg = 'Cannot reactivate subscription from %s state.' % sub.state
            return Response({"error": msg},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            sub.activate()
            sub.save()
            return Response({"state": sub.state},
                            status=status.HTTP_200_OK)


class MeteredFeatureUnitsLogDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    paginate_by = None

    def get(self, request, format=None, **kwargs):
        """
        Returns a Subscription's Metered Feature Units Log.

        The Units Log consists of multiple buckets representing billing cycles.
        """
        subscription_pk = kwargs.get('subscription_pk', None)
        mf_product_code = kwargs.get('mf_product_code', None)

        subscription = Subscription.objects.get(pk=subscription_pk)

        metered_feature = get_object_or_404(
            subscription.plan.metered_features,
            product_code__value=mf_product_code
        )

        logs = MeteredFeatureUnitsLog.objects.filter(
            metered_feature=metered_feature.pk,
            subscription=subscription_pk)

        serializer = MFUnitsLogSerializer(
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
        mf_product_code = self.kwargs.get('mf_product_code', None)
        subscription_pk = self.kwargs.get('subscription_pk', None)
        date = request.data.get('date', None)
        consumed_units = request.data.get('count', None)
        update_type = request.data.get('update_type', None)

        subscription = get_object_or_None(Subscription, pk=subscription_pk)
        metered_feature = get_object_or_404(
            subscription.plan.metered_features,
            product_code__value=mf_product_code
        )
        if subscription and metered_feature:
            if subscription.state != 'active':
                return Response({"detail": "Subscription is not active"},
                                status=status.HTTP_403_FORBIDDEN)
            if date and consumed_units is not None and update_type:
                try:
                    date = datetime.datetime.strptime(date,
                                                      '%Y-%m-%d').date()
                except TypeError:
                    return Response({'detail': 'Invalid date format. Please '
                                    'use the ISO 8601 date format.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                bsd = subscription.bucket_start_date()
                bed = subscription.bucket_end_date()
                if not bsd or not bed:
                    return Response(
                        {'detail': 'An error has been encountered.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                if date <= bsd:
                    bsdt = datetime.datetime.combine(bsd, datetime.time())
                    allowed_time = datetime.timedelta(
                        seconds=subscription.plan.generate_after)
                    if datetime.datetime.now() < bsdt + allowed_time:
                        bed = bsd
                        bsd = last_date_that_fits(
                            initial_date=subscription.start_date,
                            end_date=bed,
                            interval_type=subscription.plan.interval,
                            interval_count=subscription.plan.interval_count
                        )

                if bsd <= date <= bed:
                    if metered_feature not in \
                            subscription.plan.metered_features.all():
                        err = "The metered feature does not belong to "\
                              "the subscription's plan."
                        return Response(
                            {"detail": err},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    log = MeteredFeatureUnitsLog.objects.filter(
                        start_date=bsd,
                        end_date=bed,
                        metered_feature=metered_feature.pk,
                        subscription=subscription_pk
                    ).first()

                    if log is not None:
                        if update_type == 'absolute':
                            log.consumed_units = consumed_units
                        elif update_type == 'relative':
                            log.consumed_units += consumed_units
                        log.save()
                    else:
                        log = MeteredFeatureUnitsLog.objects.create(
                            metered_feature=metered_feature,
                            subscription=subscription,
                            start_date=bsd,
                            end_date=bed,
                            consumed_units=consumed_units
                        )
                    return Response({"count": log.consumed_units},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"detail": "Date is out of bounds"},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": "Not enough information provided"},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "Not found"},
                            status=status.HTTP_404_NOT_FOUND)


class CustomerList(HPListCreateAPIView):
    """
    **Customers Endpoint**
    """
    permission_classes = (permissions.IsAuthenticated,)
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
        `email`, `name`, `company`, `active`, `country`, `reference`,
         `sales_tax_name`, `consolidated_billing`, `sales_tax_number`.
        """
        return super(CustomerList, self).get(request, *args, **kwargs)


class CustomerDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerSerializer
    model = Customer

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        try:
            return Customer.objects.get(pk=pk)
        except (TypeError, ValueError, Customer.DoesNotExist):
            raise Http404

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


class ProductCodeListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Adds a new Product Code.
        """
        return super(ProductCodeListCreate, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Product Codes.
        """
        return super(ProductCodeListCreate, self).get(request, *args, **kwargs)


class ProductCodeRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()

    def put(self, request, *args, **kwargs):
        """
        Adds or does a full update on a Product Code.
        """
        return super(ProductCodeRetrieveUpdate, self).put(
            request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Partially updates an existing Product Code.
        """
        return super(ProductCodeRetrieveUpdate, self).patch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a specific Product Code.
        """
        return super(ProductCodeRetrieveUpdate, self).get(
            request, *args, **kwargs)


class ProviderListCreate(HPListBulkCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ProviderFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Provider.
        """
        return super(ProviderListCreate, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Providers.

        Filtering can be done with the following parameters: `email`, `company`.
        """
        return super(ProviderListCreate, self).get(request, *args, **kwargs)


class ProviderRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
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


class InvoiceListCreate(HPListCreateAPIView):
    """
    **Invoices Endpoint**
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = InvoiceFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Invoice.
        """
        return super(InvoiceListCreate, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing Invoices.

        Filtering can be done with the following parameters: `state`, `number`,
         `customer_name`, `customer_company`, `issue_date`, `due_date`,
         `paid_date`, `cancel_date`, `currency`, `sales_tax_name`, `series`
        """
        return super(InvoiceListCreate, self).get(request, *args, **kwargs)


class InvoiceRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()

    def put(self, request, *args, **kwargs):
        """
        Adds or does a full update on an Invoice.

        Modifying an invoice is only possible when it's in draft state. Also,
        take note that the invoice state cannot be updated through this method.
        """
        return super(InvoiceRetrieveUpdate, self).put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Partially updates an existing Invoice.

        Modifying an invoice is only possible when it's in draft state. Also,
        take note that the invoice state cannot be updated through this method.
        """
        return super(InvoiceRetrieveUpdate, self).patch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a specific Invoice.
        """
        return super(InvoiceRetrieveUpdate, self).get(request, *args, **kwargs)


class DocEntryCreate(generics.CreateAPIView):
    def get_model(self):
        raise NotImplementedError

    def get_model_name(self):
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        Model = self.get_model()
        model_name = self.get_model_name()

        try:
            document = Model.objects.get(pk=doc_pk)
        except Model.DoesNotExist:
            msg = "{model} not found".format(model=model_name)
            return Response({"detail": msg}, status=status.HTTP_404_NOT_FOUND)

        if document.state != 'draft':
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentEntrySerializer(data=request.DATA,
                                             context={'request': request})

        if serializer.is_valid(raise_exception=True):
            # This will be either {invoice: <invoice_object>} or
            # {proforma: <proforma_object>} as a DocumentEntry can have a
            # foreign key to either an invoice or a proforma
            extra_context = {model_name.lower(): document}
            serializer.save(**extra_context)

            return Response(serializer.data, status=status.HTTP_201_CREATED)


class InvoiceEntryCreate(DocEntryCreate):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Adds an entry to an invoice.

        This operation is only possible when the invoice is in draft state.
        """
        return super(InvoiceEntryCreate, self).post(request, *args, **kwargs)

    def get_model(self):
        return Invoice

    def get_model_name(self):
        return "Invoice"


class DocEntryUpdateDestroy(APIView):
    def put(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        entry_id = kwargs.get('entry_id')

        Model = self.get_model()
        model_name = self.get_model_name()

        document = get_object_or_404(Model, pk=doc_pk)
        if document.state != 'draft':
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        searched_fields = {model_name.lower(): document, 'entry_id': entry_id}
        entry = get_object_or_404(DocumentEntry, **searched_fields)

        serializer = DocumentEntrySerializer(entry, data=request.DATA,
                                             context={'request': request})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        doc_pk = kwargs.get('document_pk')
        entry_id = kwargs.get('entry_id')

        Model = self.get_model()
        model_name = self.get_model_name()

        document = get_object_or_404(Model, pk=doc_pk)
        if document.state != 'draft':
            msg = "{model} entries can be added only when the {model_lower} is"\
                  " in draft state.".format(model=model_name,
                                            model_lower=model_name.lower())
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        searched_fields = {model_name.lower(): document, 'entry_id': entry_id}
        entry = get_object_or_404(DocumentEntry, **searched_fields)
        entry.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_model(self):
        raise NotImplementedError

    def get_model_name(self):
        raise NotImplementedError


class InvoiceEntryUpdateDestroy(DocEntryUpdateDestroy):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def put(self, request, *args, **kwargs):
        """
        Updates an entry of an Invoice.

        This operation is only possible when the invoice is in draft state.
        """
        return super(InvoiceEntryUpdateDestroy, self).put(request, *args,
                                                          **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes an entry from an Invoice.

        This operation is only possible when the invoice is in draft state.
        """
        return super(InvoiceEntryUpdateDestroy, self).delete(request, *args,
                                                             **kwargs)

    def get_model(self):
        return Invoice

    def get_model_name(self):
        return "Invoice"


class InvoiceStateHandler(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InvoiceSerializer

    def patch(self, request, *args, **kwargs):
        """
        Used to issue, cancel or pay an Invoice.

        The operation is decided by providing the `state` field.


        ##Issuing (state = 'issued')##
        The invoice must be in `draft` state.

        When issue_date is specified, the invoice's issue_date is set to this
        value. If it's not and the invoice has no issue_date set, it it set to
        the current date.

        If due_date is specified it overwrites the invoice's due_date
        If the invoice has no billing_details set, it copies the
        billing_details from the customer. The same goes with sales_tax_percent
        and sales_tax_name
        It sets the invoice status to issued.


        ##Paying (state = 'paid')##
        The invoice must be in the issued state. Paying an invoice follows
        these steps:

        If paid_date is specified, set the invoice paid_date to this value,
        else set the invoice paid_date to the current date.
        Sets the invoice status to paid.

        ##Paying (state = 'canceled')##
        The invoice must be in the issued state. Canceling an invoice follows
        these steps:

        If cancel_date is specified, set the invoice cancel_date to this value,
        else set the invoice cancel_date to the current date.
        Sets the invoice status to paid.
        """
        invoice_pk = kwargs.get('pk')
        try:
            invoice = Invoice.objects.get(pk=invoice_pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Invoice not found"},
                            status=status.HTTP_404_NOT_FOUND)

        state = request.DATA.get('state', None)
        if state == 'issued':
            if invoice.state != 'draft':
                msg = "An invoice can be issued only if it is in draft state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            issue_date = request.DATA.get('issue_date', None)
            due_date = request.DATA.get('due_date', None)
            invoice.issue(issue_date, due_date)
            invoice.save()
        elif state == 'paid':
            if invoice.state != 'issued':
                msg = "An invoice can be paid only if it is in issued state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            paid_date = request.DATA.get('paid_date', None)
            invoice.pay(paid_date)
            invoice.save()
        elif state == 'canceled':
            if invoice.state != 'issued':
                msg = "An invoice can be canceled only if it is in issued " \
                      "state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            cancel_date = request.DATA.get('cancel_date', None)
            invoice.cancel(cancel_date)
            invoice.save()
        elif not state:
            msg = "You have to provide a value for the state field."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            msg = "Illegal state value."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvoiceSerializer(invoice, context={'request': request})
        return Response(serializer.data)


class ProformaListCreate(HPListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProformaSerializer
    queryset = Proforma.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ProformaFilter

    def post(self, request, *args, **kwargs):
        """
        Adds a new Proforma.
        """
        return super(InvoiceListCreate, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a queryset containing proformas.

        Filtering can be done with the following parameters: `state`, `number`,
         `customer_name`, `customer_company`, `issue_date`, `due_date`,
         `paid_date`, `cancel_date`, `currency`, `sales_tax_name`, `series`
        """
        return super(InvoiceListCreate, self).get(request, *args, **kwargs)


class ProformaRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProformaSerializer
    queryset = Proforma.objects.all()

    def put(self, request, *args, **kwargs):
        """
        Adds or does a full update on a Proforma.

        Modifying a proforma is only possible when it's in draft state. Also,
        take note that the proforma state cannot be updated through this method.
        """
        return super(InvoiceRetrieveUpdate, self).put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Partially updates an existing Proforma.

        Modifying a proforma is only possible when it's in draft state. Also,
        take note that the proforma state cannot be updated through this method.
        """
        return super(InvoiceRetrieveUpdate, self).patch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Returns a specific Proforma.
        """
        return super(InvoiceRetrieveUpdate, self).get(request, *args, **kwargs)


class ProformaEntryCreate(DocEntryCreate):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def post(self, request, *args, **kwargs):
        """
        Adds an entry to a Proforma.

        This operation is only possible when the proforma is in draft state.
        """
        return super(ProformaEntryCreate, self).post(request, *args, **kwargs)

    def get_model(self):
        return Proforma

    def get_model_name(self):
        return "Proforma"


class ProformaEntryUpdateDestroy(DocEntryUpdateDestroy):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = DocumentEntrySerializer
    queryset = DocumentEntry.objects.all()

    def put(self, request, *args, **kwargs):
        """
        Updates an entry of a Proforma.

        This operation is only possible when the proforma is in draft state.
        """
        return super(ProformaEntryUpdateDestroy, self).put(request, *args,
                                                           **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes an entry from a Proforma.

        This operation is only possible when the proforma is in draft state.
        """
        return super(ProformaEntryUpdateDestroy, self).delete(request, *args,
                                                              **kwargs)

    def get_model(self):
        return Proforma

    def get_model_name(self):
        return "Proforma"


class ProformaStateHandler(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProformaSerializer

    def patch(self, request, *args, **kwargs):
        """
        Used to issue, cancel or pay a Proforma.

        The operation is decided by providing the `state` field.


        ##Issuing (state = 'issued')##
        The proforma must be in `draft` state.

        When issue_date is specified, the proforma's issue_date is set to this
        value. If it's not and the proforma has no issue_date set, it it set to
        the current date.

        If due_date is specified it overwrites the proforma's due_date
        If the proforma has no billing_details set, it copies the
        billing_details from the customer. The same goes with sales_tax_percent
        and sales_tax_name
        It sets the proforma status to issued.


        ##Paying (state = 'paid')##
        The proforma must be in the issued state. Paying a proforma follows
        these steps:

        If paid_date is specified, set the proforma paid_date to this value,
        else set the proforma paid_date to the current date.
        Sets the proforma status to paid.

        ##Paying (state = 'canceled')##
        The proforma must be in the issued state. Canceling a proforma follows
        these steps:

        If cancel_date is specified, set the proforma cancel_date to this value,
        else set the proforma cancel_date to the current date.
        Sets the proforma status to paid.
        """
        proforma_pk = kwargs.get('pk')
        try:
            proforma = Proforma.objects.get(pk=proforma_pk)
        except Proforma.DoesNotExist:
            return Response({"detail": "Proforma not found"},
                            status=status.HTTP_404_NOT_FOUND)

        state = request.DATA.get('state', None)
        if state == 'issued':
            if proforma.state != 'draft':
                msg = "A proforma can be issued only if it is in draft state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            issue_date = request.DATA.get('issue_date', None)
            due_date = request.DATA.get('due_date', None)
            proforma.issue(issue_date, due_date)
            proforma.save()
        elif state == 'paid':
            if proforma.state != 'issued':
                msg = "A proforma can be paid only if it is in issued state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            paid_date = request.DATA.get('paid_date', None)
            proforma.pay(paid_date)
            proforma.save()
        elif state == 'canceled':
            if proforma.state != 'issued':
                msg = "A proforma can be canceled only if it is in issued " \
                      "state."
                return Response({"detail": msg},
                                status=status.HTTP_403_FORBIDDEN)

            cancel_date = request.DATA.get('cancel_date', None)
            proforma.cancel(cancel_date)
            proforma.save()
        elif not state:
            msg = "You have to provide a value for the state field."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)
        else:
            msg = "Illegal state value."
            return Response({"detail": msg}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProformaSerializer(proforma, context={'request': request})
        return Response(serializer.data)
