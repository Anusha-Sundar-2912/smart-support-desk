
import { LightningElement } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';

import getIssuesFiltered from '@salesforce/apex/SmartSupportApiService.getIssuesFiltered';
import getIssueSummary from '@salesforce/apex/SmartSupportApiService.getIssueSummary';
import getOrder from '@salesforce/apex/SmartSupportApiService.getOrder';
import getOrderReviews from '@salesforce/apex/SmartSupportApiService.getOrderReviews';
import getOrderItems from '@salesforce/apex/SmartSupportApiService.getOrderItems';
import getOrderPayments from '@salesforce/apex/SmartSupportApiService.getOrderPayments';
import getCustomerOrders from '@salesforce/apex/SmartSupportApiService.getCustomerOrders';
import getReviewTranslation from '@salesforce/apex/SmartSupportApiService.getReviewTranslation';

import startSyncPage from '@salesforce/apex/SmartSupportCaseService.startSyncPage';

const PAGE_SIZE = 20;
const SYNC_BATCH_SIZE = 20;

const ISSUE_CATEGORIES = [
    'Low customer rating',
    'Late delivery',
    'Low rating and late delivery',
    'Cancelled order',
    'Unavailable order',
    'Potentially overdue order'
];

function parseResponse(response) {
    return typeof response === 'string'
        ? JSON.parse(response)
        : response;
}

function extractRows(data, keys) {
    if (Array.isArray(data)) {
        return data;
    }

    if (!data || typeof data !== 'object') {
        return [];
    }

    for (const key of keys) {
        if (Array.isArray(data[key])) {
            return data[key];
        }
    }

    return [];
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString('en-IN');
}

export default class SmartSupportDashboard extends NavigationMixin(
    LightningElement
) {
    // =================================================
    // DASHBOARD DATA
    // =================================================

    issues = [];
    summary = null;

    selectedIssue = null;
    orderDetails = null;
    reviews = null;
    items = null;
    payments = null;
    customerOrders = null;

    offset = 0;
    filteredTotal = 0;
    hasMore = false;

    loading = false;
    summaryLoading = false;
    detailLoading = false;

    error = '';
    summaryError = '';
    detailError = '';

    searchTerm = '';
    issueType = 'all';
    priority = 'all';
    rating = '0';
    orderStatus = 'all';
    sortMode = 'overview';

    requestSequence = 0;
    detailSequence = 0;

    // =================================================
    // REVIEW TRANSLATION
    // =================================================

    translations = {};
    translatingReviewId = '';
    translationError = '';

    // =================================================
    // CASE SYNCHRONIZATION
    // =================================================

    syncLoading = false;
    syncMessage = '';
    syncError = '';
    syncOffset = 0;
    lastSyncJobId = '';

    connectedCallback() {
        this.refreshDashboard();
    }

    // =================================================
    // SUMMARY
    // =================================================

    get totalIssues() {
        return formatNumber(this.summary?.total);
    }

    get highPriorityCount() {
        return formatNumber(
            this.summary?.priorities?.High
        );
    }

    get mediumPriorityCount() {
        return formatNumber(
            this.summary?.priorities?.Medium
        );
    }

    get categoryCount() {
        const categories = this.summary?.categories || {};

        return Object.values(categories)
            .filter(value => Number(value) > 0)
            .length;
    }

    get categoryBreakdown() {
        const categories = this.summary?.categories || {};

        return ISSUE_CATEGORIES.map(name => ({
            name,
            count: formatNumber(categories[name] || 0)
        }));
    }

    async loadSummary() {
        this.summaryLoading = true;
        this.summaryError = '';

        try {
            const response = await getIssueSummary();
            this.summary = parseResponse(response);
        } catch (error) {
            this.summaryError = this.getErrorMessage(error);
        } finally {
            this.summaryLoading = false;
        }
    }

    // =================================================
    // FILTER OPTIONS
    // =================================================

    get issueTypeOptions() {
        return [
            { label: 'All issue categories', value: 'all' },
            ...ISSUE_CATEGORIES.map(name => ({
                label: name,
                value: name
            }))
        ];
    }

    get priorityOptions() {
        return [
            { label: 'All priorities', value: 'all' },
            { label: 'High', value: 'High' },
            { label: 'Medium', value: 'Medium' },
            { label: 'Low', value: 'Low' }
        ];
    }

    get ratingOptions() {
        return [
            { label: 'All ratings', value: '0' },
            { label: '1 star', value: '1' },
            { label: '2 stars', value: '2' },
            { label: '3 stars', value: '3' },
            { label: '4 stars', value: '4' },
            { label: '5 stars', value: '5' },
            { label: 'Not rated', value: '-1' }
        ];
    }

    get orderStatusOptions() {
        return [
            { label: 'All order statuses', value: 'all' },
            { label: 'Delivered', value: 'delivered' },
            { label: 'Shipped', value: 'shipped' },
            { label: 'Cancelled', value: 'canceled' },
            { label: 'Unavailable', value: 'unavailable' },
            { label: 'Invoiced', value: 'invoiced' },
            { label: 'Processing', value: 'processing' },
            { label: 'Created', value: 'created' },
            { label: 'Approved', value: 'approved' }
        ];
    }

    get sortOptions() {
        return [
            { label: 'Balanced overview', value: 'overview' },
            { label: 'Priority first', value: 'priority' },
            { label: 'Most recent', value: 'recent' }
        ];
    }

    // =================================================
    // FILTER HANDLERS
    // =================================================

    handleSearchChange(event) {
        this.searchTerm = event.target.value || '';
    }

    handleIssueTypeChange(event) {
        this.issueType = event.detail.value;
    }

    handlePriorityChange(event) {
        this.priority = event.detail.value;
    }

    handleRatingChange(event) {
        this.rating = event.detail.value;
    }

    handleOrderStatusChange(event) {
        this.orderStatus = event.detail.value;
    }

    handleSortChange(event) {
        this.sortMode = event.detail.value;
    }

    handleApplyFilters() {
        this.offset = 0;
        this.loadIssues();
    }

    handleClearFilters() {
        this.searchTerm = '';
        this.issueType = 'all';
        this.priority = 'all';
        this.rating = '0';
        this.orderStatus = 'all';
        this.sortMode = 'overview';
        this.offset = 0;

        this.loadIssues();
    }

    // =================================================
    // ISSUE EXPLORER
    // =================================================

    get hasIssues() {
        return this.issues.length > 0;
    }

    get showEmptyState() {
        return !this.loading &&
            !this.error &&
            this.issues.length === 0;
    }

    get formattedIssues() {
        return this.issues.map(issue => {
            const priorityValue = issue.priority || 'Low';

            let priorityClass = 'priority-badge priority-low';

            if (priorityValue === 'High') {
                priorityClass = 'priority-badge priority-high';
            } else if (priorityValue === 'Medium') {
                priorityClass = 'priority-badge priority-medium';
            }

            const city = issue.customer_city || '';
            const state = issue.customer_state || '';

            return {
                ...issue,
                priorityClass,
                ratingDisplay:
                    issue.lowest_rating === null ||
                    issue.lowest_rating === undefined
                        ? 'Not rated'
                        : `${issue.lowest_rating}/5`,
                locationDisplay:
                    [city, state].filter(Boolean).join(', ') ||
                    'Unknown'
            };
        });
    }

    get pageNumber() {
        return Math.floor(this.offset / PAGE_SIZE) + 1;
    }

    get rangeStart() {
        return this.filteredTotal > 0
            ? this.offset + 1
            : 0;
    }

    get rangeEnd() {
        return this.offset + this.issues.length;
    }

    get disablePrevious() {
        return this.loading || this.offset === 0;
    }

    get disableNext() {
        return this.loading || !this.hasMore;
    }

    async loadIssues() {
        const requestId = ++this.requestSequence;

        this.loading = true;
        this.error = '';

        try {
            const response = await getIssuesFiltered({
                limitSize: PAGE_SIZE,
                offsetSize: this.offset,
                issueType: this.issueType,
                priority: this.priority,
                rating: Number(this.rating),
                orderStatus: this.orderStatus,
                searchTerm: this.searchTerm.trim(),
                sortMode: this.sortMode
            });

            if (requestId !== this.requestSequence) {
                return;
            }

            const data = parseResponse(response);

            this.issues = Array.isArray(data.issues)
                ? data.issues
                : [];

            this.filteredTotal = Number(data.total || 0);
            this.hasMore = Boolean(data.has_more);

        } catch (error) {
            if (requestId !== this.requestSequence) {
                return;
            }

            this.error = this.getErrorMessage(error);
            this.issues = [];
            this.filteredTotal = 0;
            this.hasMore = false;

        } finally {
            if (requestId === this.requestSequence) {
                this.loading = false;
            }
        }
    }

    async refreshDashboard() {
        await Promise.all([
            this.loadSummary(),
            this.loadIssues()
        ]);
    }

    handleRefresh() {
        this.refreshDashboard();
    }

    handleNext() {
        if (this.disableNext) {
            return;
        }

        this.offset += PAGE_SIZE;
        this.loadIssues();
    }

    handlePrevious() {
        if (this.disablePrevious) {
            return;
        }

        this.offset = Math.max(
            0,
            this.offset - PAGE_SIZE
        );

        this.loadIssues();
    }

    // =================================================
    // INVESTIGATION WORKSPACE
    // =================================================

    get hasSelection() {
        return this.selectedIssue !== null;
    }

    get selectedOrderId() {
        return this.selectedIssue?.order_id || '';
    }

    get selectedCustomerId() {
        return this.selectedIssue?.customer_unique_id || '';
    }

    get reviewRows() {
        const rows = extractRows(this.reviews, [
            'reviews',
            'results',
            'data'
        ]);

        return rows.map((row, index) => {
            const reviewId = row.review_id;
            const translation = this.translations[reviewId];

            return {
                ...row,
                review_id: reviewId || `review-${index}`,
                translatedTitle:
                    translation?.translated_title || '',
                translatedMessage:
                    translation?.translated_message || '',
                hasTranslation: Boolean(
                    translation &&
                    translation.translation_status === 'translated'
                ),
                isTranslating:
                    this.translatingReviewId === reviewId,
                disableTranslate:
                    !reviewId ||
                    this.translatingReviewId !== '' ||
                    Boolean(translation),
                hasReviewText: Boolean(
                    row.review_comment_title ||
                    row.review_comment_message
                )
            };
        });
    }

    get itemRows() {
        const rows = extractRows(this.items, [
            'items',
            'order_items',
            'results',
            'data'
        ]);

        return rows.map((row, index) => ({
            ...row,
            order_item_id:
                `${row.order_item_id || index}-${index}`,
            product_category:
                row.product_category_name_english ||
                row.product_category_name ||
                row.product_category ||
                'Not specified'
        }));
    }

    get paymentRows() {
        const rows = extractRows(this.payments, [
            'payments',
            'results',
            'data'
        ]);

        return rows.map((row, index) => ({
            ...row,
            key: `${row.payment_sequential || index}-${index}`
        }));
    }

    get customerOrderRows() {
        return extractRows(this.customerOrders, [
            'orders',
            'results',
            'data'
        ]);
    }

    get hasReviews() {
        return this.reviewRows.length > 0;
    }

    get hasItems() {
        return this.itemRows.length > 0;
    }

    get hasPayments() {
        return this.paymentRows.length > 0;
    }

    get hasCustomerOrders() {
        return this.customerOrderRows.length > 0;
    }

    async handleSelectIssue(event) {
        const orderId = event.currentTarget.dataset.id;

        const issue = this.issues.find(
            row => row.order_id === orderId
        );

        if (!issue) {
            return;
        }

        const requestId = ++this.detailSequence;

        this.selectedIssue = issue;
        this.orderDetails = null;
        this.reviews = null;
        this.items = null;
        this.payments = null;
        this.customerOrders = null;

        this.translations = {};
        this.translatingReviewId = '';
        this.translationError = '';

        this.detailError = '';
        this.detailLoading = true;

        try {
            const results = await Promise.allSettled([
                getOrder({ orderId }),
                getOrderReviews({ orderId }),
                getOrderItems({ orderId }),
                getOrderPayments({ orderId }),
                getCustomerOrders({
                    customerId: issue.customer_unique_id
                })
            ]);

            if (requestId !== this.detailSequence) {
                return;
            }

            const properties = [
                'orderDetails',
                'reviews',
                'items',
                'payments',
                'customerOrders'
            ];

            const errors = [];

            results.forEach((result, index) => {
                if (result.status === 'fulfilled') {
                    try {
                        this[properties[index]] = parseResponse(
                            result.value
                        );
                    } catch (error) {
                        errors.push(
                            `${properties[index]}: ${
                                this.getErrorMessage(error)
                            }`
                        );
                    }
                } else {
                    errors.push(
                        `${properties[index]}: ${
                            this.getErrorMessage(result.reason)
                        }`
                    );
                }
            });

            if (errors.length > 0) {
                this.detailError =
                    'Some investigation sections could not load. ' +
                    errors.join(' | ');
            }

        } catch (error) {
            if (requestId === this.detailSequence) {
                this.detailError = this.getErrorMessage(error);
            }

        } finally {
            if (requestId === this.detailSequence) {
                this.detailLoading = false;
            }
        }
    }

    handleCloseDetails() {
        ++this.detailSequence;

        this.selectedIssue = null;
        this.orderDetails = null;
        this.reviews = null;
        this.items = null;
        this.payments = null;
        this.customerOrders = null;

        this.translations = {};
        this.translatingReviewId = '';
        this.translationError = '';

        this.detailError = '';
        this.detailLoading = false;
    }

    // =================================================
    // REVIEW TRANSLATION
    // =================================================

    async handleTranslateReview(event) {
        const reviewId = event.currentTarget.dataset.id;

        if (!reviewId || this.translatingReviewId) {
            return;
        }

        const requestId = this.detailSequence;

        this.translatingReviewId = reviewId;
        this.translationError = '';

        try {
            const response = await getReviewTranslation({
                reviewId
            });

            if (requestId !== this.detailSequence) {
                return;
            }

            const result = parseResponse(response);

            this.translations = {
                ...this.translations,
                [reviewId]: result
            };

        } catch (error) {
            if (requestId === this.detailSequence) {
                this.translationError =
                    this.getErrorMessage(error);
            }

        } finally {
            if (requestId === this.detailSequence) {
                this.translatingReviewId = '';
            }
        }
    }

    // =================================================
    // SALESFORCE CASE SYNCHRONIZATION
    // =================================================

    get disableSync() {
        return this.syncLoading ||
            (this.summary !== null &&
             this.syncOffset >= Number(this.summary.total || 0));
    }

    get syncProgressLabel() {
        const total = Number(this.summary?.total || 0);
        const start = this.syncOffset + 1;
        const end = total > 0
            ? Math.min(this.syncOffset + SYNC_BATCH_SIZE, total)
            : this.syncOffset + SYNC_BATCH_SIZE;

        return `Next batch: ${start}–${end}`;
    }

    async handleSyncCases() {
        if (this.disableSync) {
            return;
        }

        this.syncLoading = true;
        this.syncError = '';
        this.syncMessage = '';

        try {
            const currentOffset = this.syncOffset;

            const jobId = await startSyncPage({
                limitSize: SYNC_BATCH_SIZE,
                offsetSize: currentOffset
            });

            if (!jobId) {
                throw new Error(
                    'Salesforce did not return a synchronization job ID.'
                );
            }

            this.lastSyncJobId = jobId;

            const start = currentOffset + 1;
            const end = currentOffset + SYNC_BATCH_SIZE;

            this.syncMessage =
                `Batch ${start}–${end} was queued. ` +
                `Job ID: ${jobId}. ` +
                'This confirms job submission, not Case creation. ' +
                'Check the job and Salesforce Cases before continuing.';

            // The next page can be queued manually.
            // This is not proof the previous job succeeded.
            this.syncOffset += SYNC_BATCH_SIZE;

        } catch (error) {
            this.syncError = this.getErrorMessage(error);

        } finally {
            this.syncLoading = false;
        }
    }

    handleResetSyncOffset() {
        if (this.syncLoading) {
            return;
        }

        this.syncOffset = 0;
        this.syncMessage = '';
        this.syncError = '';
        this.lastSyncJobId = '';
    }

    // =================================================
    // SALESFORCE NAVIGATION
    // =================================================

    handleOpenCases() {
        this[NavigationMixin.Navigate]({
            type: 'standard__objectPage',
            attributes: {
                objectApiName: 'Case',
                actionName: 'list'
            }
        });
    }

    // =================================================
    // ERROR HANDLING
    // =================================================

    getErrorMessage(error) {
        if (Array.isArray(error?.body)) {
            return error.body
                .map(item => item.message)
                .join(', ');
        }

        return error?.body?.message ||
            error?.message ||
            'An unexpected error occurred.';
    }
}
