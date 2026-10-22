
public with sharing class SmartSupportCaseService
    implements Queueable, Database.AllowsCallouts {

    private Integer batchSize;
    private Integer offsetSize;

    public SmartSupportCaseService(Integer batchSize) {
        this(batchSize, 0);
    }

    public SmartSupportCaseService(
        Integer batchSize,
        Integer offsetSize
    ) {
        this.batchSize = batchSize == null
            ? 20
            : Math.max(1, Math.min(batchSize, 100));

        this.offsetSize = offsetSize == null
            ? 0
            : Math.max(0, offsetSize);
    }

    @AuraEnabled
    public static String startSync(Integer limitSize) {
        return startSyncPage(limitSize, 0);
    }

    @AuraEnabled
    public static String startSyncPage(
        Integer limitSize,
        Integer offsetSize
    ) {
        Integer safeLimit = limitSize == null
            ? 20
            : Math.max(1, Math.min(limitSize, 100));

        Integer safeOffset = offsetSize == null
            ? 0
            : Math.max(0, offsetSize);

        Id jobId = System.enqueueJob(
            new SmartSupportCaseService(
                safeLimit,
                safeOffset
            )
        );

        return String.valueOf(jobId);
    }

    public void execute(QueueableContext context) {

        // Perform the REST callout before Salesforce DML.
        String jsonResponse =
            SmartSupportApiService.getIssuesPaginated(
                batchSize,
                offsetSize
            );

        Map<String, Object> payload =
            (Map<String, Object>)
            JSON.deserializeUntyped(jsonResponse);

        if (payload == null) {
            throw new SmartSupportSyncException(
                'The backend returned an empty response.'
            );
        }

        List<Object> issues =
            (List<Object>) payload.get('issues');

        if (issues == null || issues.isEmpty()) {
            System.debug(
                'SMART SUPPORT: No issues found for offset ' +
                offsetSize
            );
            return;
        }

        Set<String> orderIds = new Set<String>();

        for (Object item : issues) {
            Map<String, Object> issue =
                (Map<String, Object>) item;

            String orderId =
                (String) issue.get('order_id');

            if (!String.isBlank(orderId)) {
                orderIds.add(orderId);
            }
        }

        Map<String, Case> existingCases =
            new Map<String, Case>();

        for (Case existing : [
            SELECT Id, Olist_Order_ID__c
            FROM Case
            WHERE Olist_Order_ID__c IN :orderIds
        ]) {
            existingCases.put(
                existing.Olist_Order_ID__c,
                existing
            );
        }

        List<Case> casesToCreate = new List<Case>();
        Set<String> processedOrderIds = new Set<String>();

        for (Object item : issues) {

            Map<String, Object> issue =
                (Map<String, Object>) item;

            String orderId =
                (String) issue.get('order_id');

            if (
                String.isBlank(orderId) ||
                existingCases.containsKey(orderId) ||
                processedOrderIds.contains(orderId)
            ) {
                continue;
            }

            processedOrderIds.add(orderId);

            String reason =
                (String) issue.get('issue_reason');

            String priority =
                (String) issue.get('priority');

            if (
                priority != 'High' &&
                priority != 'Medium' &&
                priority != 'Low'
            ) {
                priority = 'Medium';
            }

            Boolean delayed =
                issue.get('delivered_late') == true;

            Decimal rating = null;

            if (issue.get('lowest_rating') != null) {
                rating = Decimal.valueOf(
                    String.valueOf(
                        issue.get('lowest_rating')
                    )
                );
            }

            Case supportCase = new Case();

            supportCase.Subject =
                'Order Support - ' + orderId;

            supportCase.Status = 'New';
            supportCase.Origin = 'Web';
            supportCase.Priority = priority;

            supportCase.Description =
                'Automatically identified from the ' +
                'historical Olist e-commerce dataset.' +
                '\nIssue: ' + reason +
                '\nOrder ID: ' + orderId +
                '\nOrder Status: ' +
                String.valueOf(issue.get('order_status')) +
                '\nPriority: ' + priority +
                '\nDelivered Late: ' +
                String.valueOf(delayed) +
                '\nReview Rating: ' +
                String.valueOf(rating);

            supportCase.Olist_Order_ID__c = orderId;

            supportCase.Olist_Customer_ID__c =
                (String) issue.get('customer_unique_id');

            supportCase.Delivery_Delayed__c = delayed;
            supportCase.Review_Rating__c = rating;

            if (!String.isBlank(reason)) {
                supportCase.Issue_Reason__c = reason;
            }

            casesToCreate.add(supportCase);
        }

        if (casesToCreate.isEmpty()) {
            System.debug(
                'SMART SUPPORT: All orders on this page ' +
                'already have Salesforce Cases.'
            );
            return;
        }

        // Savepoint lets us roll back partial inserts
        // if one or more records fail validation.
        Savepoint savepointBeforeInsert =
            Database.setSavepoint();

        Database.SaveResult[] results =
            Database.insert(casesToCreate, false);

        Integer created = 0;
        Integer failed = 0;
        List<String> errorMessages = new List<String>();

        for (Integer i = 0; i < results.size(); i++) {

            if (results[i].isSuccess()) {
                created++;
            } else {
                failed++;

                for (Database.Error insertError :
                    results[i].getErrors()) {

                    String message =
                        'Order ' +
                        casesToCreate[i].Olist_Order_ID__c +
                        ': ' +
                        insertError.getMessage();

                    errorMessages.add(message);

                    System.debug(
                        LoggingLevel.ERROR,
                        'SMART SUPPORT CASE ERROR - ' +
                        message
                    );
                }
            }
        }

        if (failed > 0) {
            Database.rollback(savepointBeforeInsert);

            throw new SmartSupportSyncException(
                'Case synchronization failed for ' +
                failed +
                ' of ' +
                casesToCreate.size() +
                ' records. The batch was rolled back. ' +
                String.join(errorMessages, ' | ')
            );
        }

        System.debug(
            'SMART SUPPORT SYNC COMPLETE' +
            '\nOffset: ' + offsetSize +
            '\nFetched: ' + issues.size() +
            '\nCreated: ' + created +
            '\nAlready Existing or Skipped: ' +
            (issues.size() - casesToCreate.size())
        );
    }

    public class SmartSupportSyncException extends Exception {}
}
