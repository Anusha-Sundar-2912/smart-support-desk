public class SmartSupportCalloutTest implements Queueable, Database.AllowsCallouts {
    public void execute(QueueableContext context) {
        try {
            String response = SmartSupportApiService.getIssues(1);
            System.debug('SMART SUPPORT SUCCESS: ' + response);
        } catch (Exception e) {
            System.debug('SMART SUPPORT ERROR: ' + e.getMessage());
        }
    }
}