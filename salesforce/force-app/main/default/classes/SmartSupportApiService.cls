
public with sharing class SmartSupportApiService {

    private static final String BASE_URL =
        'callout:Smart_Support_Desk_API';

    // --------------------------------------------------
    // SECURE REST API INTEGRATION
    // --------------------------------------------------

    private static String sendGetRequest(String path) {
        HttpRequest req = new HttpRequest();

        req.setEndpoint(BASE_URL + path);
        req.setMethod('GET');

        // Allow additional time for Render free-tier cold starts.
        req.setTimeout(120000);

        HttpResponse res = new Http().send(req);

        if (res.getStatusCode() != 200) {
            throw new AuraHandledException(
                'Smart Support API returned HTTP ' +
                res.getStatusCode() + ': ' +
                res.getBody()
            );
        }

        return res.getBody();
    }

    private static String encode(String value) {
        return EncodingUtil.urlEncode(value, 'UTF-8');
    }

    // --------------------------------------------------
    // ISSUE SYNCHRONIZATION
    // --------------------------------------------------

    @AuraEnabled
    public static String getIssues(Integer limitSize) {
        return getIssuesPaginated(limitSize, 0);
    }

    @AuraEnabled
    public static String getIssuesPaginated(
        Integer limitSize,
        Integer offsetSize
    ) {
        return getIssuesFiltered(
            limitSize,
            offsetSize,
            'all',
            'all',
            0,
            'all',
            '',
            'overview'
        );
    }

    // --------------------------------------------------
    // ISSUE EXPLORER
    // --------------------------------------------------

    @AuraEnabled
    public static String getIssuesFiltered(
        Integer limitSize,
        Integer offsetSize,
        String issueType,
        String priority,
        Integer rating,
        String orderStatus,
        String searchTerm,
        String sortMode
    ) {
        Integer safeLimit = limitSize == null
            ? 20
            : Math.max(1, Math.min(limitSize, 100));

        Integer safeOffset = offsetSize == null
            ? 0
            : Math.max(0, offsetSize);

        Integer safeRating = rating == null
            ? 0
            : rating;

        if (safeRating < -1 || safeRating > 5) {
            throw new AuraHandledException(
                'Invalid rating filter'
            );
        }

        String typeValue = String.isBlank(issueType)
            ? 'all'
            : issueType;

        String priorityValue = String.isBlank(priority)
            ? 'all'
            : priority;

        String statusValue = String.isBlank(orderStatus)
            ? 'all'
            : orderStatus;

        String sortValue = String.isBlank(sortMode)
            ? 'overview'
            : sortMode;

        String searchValue = String.isBlank(searchTerm)
            ? ''
            : searchTerm.trim();

        if (searchValue.length() > 100) {
            throw new AuraHandledException(
                'Search must be 100 characters or fewer'
            );
        }

        String path =
            '/api/v1/issues?limit=' + safeLimit +
            '&offset=' + safeOffset +
            '&issue_type=' + encode(typeValue) +
            '&priority=' + encode(priorityValue) +
            '&rating=' + safeRating +
            '&order_status=' + encode(statusValue) +
            '&search=' + encode(searchValue) +
            '&sort=' + encode(sortValue);

        return sendGetRequest(path);
    }

    // --------------------------------------------------
    // DASHBOARD ANALYTICS
    // --------------------------------------------------

    @AuraEnabled
    public static String getIssueSummary() {
        return sendGetRequest(
            '/api/v1/issues/summary'
        );
    }

    // --------------------------------------------------
    // ORDER INVESTIGATION
    // --------------------------------------------------

    @AuraEnabled
    public static String getOrder(String orderId) {
        if (String.isBlank(orderId)) {
            throw new AuraHandledException(
                'Order ID is required'
            );
        }

        return sendGetRequest(
            '/api/v1/orders/' + encode(orderId)
        );
    }

    @AuraEnabled
    public static String getOrderReviews(String orderId) {
        if (String.isBlank(orderId)) {
            throw new AuraHandledException(
                'Order ID is required'
            );
        }

        return sendGetRequest(
            '/api/v1/orders/' +
            encode(orderId) +
            '/reviews'
        );
    }

    @AuraEnabled
    public static String getOrderItems(String orderId) {
        if (String.isBlank(orderId)) {
            throw new AuraHandledException(
                'Order ID is required'
            );
        }

        return sendGetRequest(
            '/api/v1/orders/' +
            encode(orderId) +
            '/items'
        );
    }

    @AuraEnabled
    public static String getOrderPayments(String orderId) {
        if (String.isBlank(orderId)) {
            throw new AuraHandledException(
                'Order ID is required'
            );
        }

        return sendGetRequest(
            '/api/v1/orders/' +
            encode(orderId) +
            '/payments'
        );
    }

    // --------------------------------------------------
    // CUSTOMER HISTORY
    // --------------------------------------------------

    @AuraEnabled
    public static String getCustomerOrders(
        String customerId
    ) {
        if (String.isBlank(customerId)) {
            throw new AuraHandledException(
                'Customer ID is required'
            );
        }

        return sendGetRequest(
            '/api/v1/customers/' +
            encode(customerId) +
            '/orders?limit=20&offset=0'
        );
    }

    // --------------------------------------------------
    // PORTUGUESE TO ENGLISH REVIEW TRANSLATION
    // --------------------------------------------------

    @AuraEnabled
    public static String getReviewTranslation(
        String reviewId
    ) {
        if (String.isBlank(reviewId)) {
            throw new AuraHandledException(
                'Review ID is required'
            );
        }

        return sendGetRequest(
            '/api/v1/reviews/' +
            encode(reviewId) +
            '/translation'
        );
    }
}
